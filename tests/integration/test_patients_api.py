from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User


class PatientsAPIIntegrationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="patient.doc@example.com",
            name="Dr. Smith",
            password="Password123!"
        )
        self.other_user = User.objects.create_user(
            email="other.doc@example.com",
            name="Dr. Jones",
            password="Password123!"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_patient_requires_idempotency_key(self):
        payload = {
            "name": "Rahul Verma",
            "date_of_birth": "1992-04-10",
            "gender": "Male",
            "phone": "9876543210"
        }
        # Missing Idempotency-Key header -> 400
        res = self.client.post("/api/patients/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(res.data["success"])
        self.assertEqual(res.data["error"]["code"], "MISSING_IDEMPOTENCY_KEY")

    def test_create_patient_with_idempotency_replay(self):
        payload = {
            "name": "Rahul Verma",
            "date_of_birth": "1992-04-10",
            "gender": "Male",
            "phone": "9876543210"
        }
        headers = {"HTTP_IDEMPOTENCY_KEY": "patient-creation-key-001"}

        # First request creates resource
        res1 = self.client.post("/api/patients/", payload, format="json", **headers)
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        patient_id = res1.data["data"]["id"]
        self.assertEqual(res1.data["data"]["version"], 1)

        # Retry with same idempotency key replays response and does NOT create a duplicate patient
        res2 = self.client.post("/api/patients/", payload, format="json", **headers)
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res2.data["data"]["id"], patient_id)
        self.assertEqual(res2.headers.get("X-Cache"), "HIT")

        # Retry with same key but altered payload returns 409 conflict
        altered_payload = {**payload, "name": "Rahul Sharma"}
        res3 = self.client.post("/api/patients/", altered_payload, format="json", **headers)
        self.assertEqual(res3.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(res3.data["error"]["code"], "IDEMPOTENCY_CONFLICT")

    def test_optimistic_locking_update(self):
        headers = {"HTTP_IDEMPOTENCY_KEY": "patient-update-test-key"}
        create_res = self.client.post(
            "/api/patients/",
            {
                "name": "Bruce Wayne",
                "date_of_birth": "1980-02-19",
                "gender": "Male"
            },
            format="json",
            **headers
        )
        patient_id = create_res.data["data"]["id"]

        # Successful update with matching version 1
        update_res = self.client.put(
            f"/api/patients/{patient_id}/",
            {
                "name": "Bruce Wayne (Batman)",
                "date_of_birth": "1980-02-19",
                "gender": "Male",
                "version": 1
            },
            format="json"
        )
        self.assertEqual(update_res.status_code, status.HTTP_200_OK)
        self.assertEqual(update_res.data["data"]["version"], 2)

        # Stale update with version 1 -> 409 Conflict
        stale_res = self.client.put(
            f"/api/patients/{patient_id}/",
            {
                "name": "Bruce Wayne Conflict",
                "date_of_birth": "1980-02-19",
                "gender": "Male",
                "version": 1
            },
            format="json"
        )
        self.assertEqual(stale_res.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(stale_res.data["error"]["code"], "OPTIMISTIC_LOCK_CONFLICT")

    def test_creator_only_permissions(self):
        create_res = self.client.post(
            "/api/patients/",
            {"name": "Clark Kent", "date_of_birth": "1985-06-18", "gender": "Male"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="clark-key"
        )
        patient_id = create_res.data["data"]["id"]

        # Switch authentication to other_user
        self.client.force_authenticate(user=self.other_user)

        # Other user cannot view or update Clark Kent
        get_res = self.client.get(f"/api/patients/{patient_id}/")
        self.assertEqual(get_res.status_code, status.HTTP_403_FORBIDDEN)

        put_res = self.client.put(
            f"/api/patients/{patient_id}/",
            {"name": "Hacked", "date_of_birth": "1985-06-18", "gender": "Male", "version": 1},
            format="json"
        )
        self.assertEqual(put_res.status_code, status.HTTP_403_FORBIDDEN)
