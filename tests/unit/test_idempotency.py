from django.test import TestCase
from apps.accounts.models import User
from common.idempotency.services import (
    calculate_request_hash,
    sanitize_response_data,
    IdempotencyService
)
from common.exceptions import IdempotencyConflictError, ValidationError


class IdempotencyUnitTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="idem@example.com", name="Idem User", password="password123")

    def test_request_hash_determinism(self):
        dict_a = {"name": "Test", "age": 30, "gender": "M"}
        dict_b = {"gender": "M", "name": "Test", "age": 30}

        # Key ordering must not affect the hash
        hash_a = calculate_request_hash(dict_a)
        hash_b = calculate_request_hash(dict_b)
        self.assertEqual(hash_a, hash_b)

        # Different payload produces different hash
        hash_c = calculate_request_hash({"name": "Different"})
        self.assertNotEqual(hash_a, hash_c)

    def test_sanitize_response_data(self):
        raw = {
            "id": 1,
            "name": "Admin",
            "password": "supersecretpassword",
            "tokens": {
                "access": "jwt-token-string",
                "refresh": "refresh-token-string"
            }
        }
        sanitized = sanitize_response_data(raw)
        self.assertEqual(sanitized["password"], "[REDACTED]")
        self.assertEqual(sanitized["tokens"]["access"], "[REDACTED]")
        self.assertEqual(sanitized["name"], "Admin")

    def test_idempotency_service_replay_and_conflict(self):
        counter = {"calls": 0}

        def mock_op():
            counter["calls"] += 1
            return {"resource_id": 101, "status": "created"}, 201

        # First execution
        data, status, replayed = IdempotencyService.execute_with_idempotency(
            user=self.user,
            endpoint="/api/test/",
            idempotency_key="key-abc-123",
            request_data={"item": "Widget"},
            operation_callable=mock_op
        )
        self.assertEqual(status, 201)
        self.assertFalse(replayed)
        self.assertEqual(counter["calls"], 1)

        # Second execution with exact same key and data -> Replayed, operation not run again
        replay_data, replay_status, is_replayed = IdempotencyService.execute_with_idempotency(
            user=self.user,
            endpoint="/api/test/",
            idempotency_key="key-abc-123",
            request_data={"item": "Widget"},
            operation_callable=mock_op
        )
        self.assertEqual(replay_status, 201)
        self.assertTrue(is_replayed)
        self.assertEqual(counter["calls"], 1)  # Did not increment

        # Third execution with same key but DIFFERENT data -> IdempotencyConflictError
        with self.assertRaises(IdempotencyConflictError):
            IdempotencyService.execute_with_idempotency(
                user=self.user,
                endpoint="/api/test/",
                idempotency_key="key-abc-123",
                request_data={"item": "Completely Different Widget"},
                operation_callable=mock_op
            )
