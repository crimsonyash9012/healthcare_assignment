import concurrent.futures
from django.test import TransactionTestCase
from django.db import connection
from apps.accounts.models import User
from apps.patients.models import Patient
from common.idempotency.services import IdempotencyService
from common.idempotency.models import IdempotencyKey


class ConcurrentIdempotencyTestCase(TransactionTestCase):
    """
    Automated concurrency test verifying that simultaneous requests with the same
    idempotency key create exactly ONE resource without raising race condition errors.
    """
    def setUp(self):
        connection.close()
        self.user = User.objects.create_user(
            email="idem.race@example.com",
            name="Race User",
            password="Password123!"
        )

    def test_concurrent_identical_requests(self):
        created_counter = {"count": 0}

        def create_patient_op():
            created_counter["count"] += 1
            patient = Patient.objects.create(
                created_by=self.user,
                name="Atomic Patient",
                date_of_birth="1995-12-12",
                gender="Female"
            )
            return {"id": patient.id, "name": patient.name}, 201

        shared_key = "concurrent-idem-key-999"
        endpoint = "/api/patients/"
        payload = {"name": "Atomic Patient", "date_of_birth": "1995-12-12", "gender": "Female"}

        responses = []

        errors = []

        def worker():
            connection.close()
            try:
                data, status_code, replayed = IdempotencyService.execute_with_idempotency(
                    user=self.user,
                    endpoint=endpoint,
                    idempotency_key=shared_key,
                    request_data=payload,
                    operation_callable=create_patient_op
                )
                responses.append((data, status_code, replayed))
            except Exception as e:
                errors.append(e)
            finally:
                connection.close()

        # Fire 2 concurrent workers with the exact same idempotency key and payload
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker) for _ in range(2)]
            concurrent.futures.wait(futures)

        self.assertEqual(len(errors), 0, f"Worker encountered errors: {errors}")
        self.assertEqual(len(responses), 2)
        # Verify that both workers received the exact same resource ID
        first_id = responses[0][0]["id"]
        second_id = responses[1][0]["id"]
        self.assertEqual(first_id, second_id)

        # Verify that only 1 record exists in the database
        self.assertEqual(Patient.objects.filter(name="Atomic Patient").count(), 1)
        self.assertEqual(IdempotencyKey.objects.filter(key=shared_key).count(), 1)
