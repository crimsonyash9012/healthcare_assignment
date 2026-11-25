from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User


class DoctorsAPIIntegrationTestCase(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            email="doctor.creator@example.com",
            name="Clinic Admin",
            password="Password123!"
        )
        self.other_user = User.objects.create_user(
            email="other.staff@example.com",
            name="Other Staff",
            password="Password123!"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.creator)

    def test_create_doctor_with_idempotency(self):
        payload = {
            "name": "Leonard McCoy",
            "specialization": "General Surgery",
            "email": "mccoy@starfleet.com",
            "experience_years": 15
        }
        headers = {"HTTP_IDEMPOTENCY_KEY": "doctor-create-001"}

        res = self.client.post("/api/doctors/", payload, format="json", **headers)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        doc_id = res.data["data"]["id"]

        # Replay with same key
        replay_res = self.client.post("/api/doctors/", payload, format="json", **headers)
        self.assertEqual(replay_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(replay_res.data["data"]["id"], doc_id)

    def test_view_allowed_for_any_user_update_restricted_to_creator(self):
        # Create doctor as creator
        res = self.client.post(
            "/api/doctors/",
            {
                "name": "Beverly Crusher",
                "specialization": "Internal Medicine",
                "email": "crusher@starfleet.com",
                "experience_years": 12
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY="doc-crusher-key"
        )
        doc_id = res.data["data"]["id"]

        # Authenticate as other_user
        self.client.force_authenticate(user=self.other_user)

        # Other user CAN view doctors (Read-only allowed)
        view_res = self.client.get(f"/api/doctors/{doc_id}/")
        self.assertEqual(view_res.status_code, status.HTTP_200_OK)

        # Other user CANNOT update doctor (Creator only)
        update_res = self.client.put(
            f"/api/doctors/{doc_id}/",
            {
                "name": "Beverly Crusher Updated",
                "specialization": "Internal Medicine",
                "email": "crusher@starfleet.com",
                "experience_years": 13,
                "version": 1
            },
            format="json"
        )
        self.assertEqual(update_res.status_code, status.HTTP_403_FORBIDDEN)
