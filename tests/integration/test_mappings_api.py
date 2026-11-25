from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date
from apps.accounts.models import User
from apps.patients.services import PatientService
from apps.doctors.services import DoctorService


class MappingsAPIIntegrationTestCase(TestCase):
    def setUp(self):
        self.patient_owner = User.objects.create_user(
            email="owner@example.com",
            name="Patient Owner",
            password="Password123!"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            name="Other User",
            password="Password123!"
        )

        self.patient = PatientService.create_patient(
            user=self.patient_owner,
            data={"name": "Mapping Patient", "date_of_birth": date(1995, 3, 10), "gender": "Female"}
        )
        self.doctor = DoctorService.create_doctor(
            user=self.other_user,
            data={"name": "Dr. Assigned", "specialization": "Cardiology", "email": "cardio@example.com"}
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.patient_owner)

    def test_assign_doctor_with_idempotency_and_authorization(self):
        payload = {
            "patient_id": self.patient.id,
            "doctor_id": self.doctor.id
        }
        headers = {"HTTP_IDEMPOTENCY_KEY": "mapping-key-101"}

        # Patient owner can assign doctor
        res = self.client.post("/api/mappings/", payload, format="json", **headers)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        mapping_id = res.data["data"]["id"]

        # Retry with same idempotency key returns cached response
        replay_res = self.client.post("/api/mappings/", payload, format="json", **headers)
        self.assertEqual(replay_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(replay_res.data["data"]["id"], mapping_id)

    def test_other_user_cannot_assign_or_delete_mapping(self):
        # Patient owner creates mapping
        res = self.client.post(
            "/api/mappings/",
            {"patient_id": self.patient.id, "doctor_id": self.doctor.id},
            format="json",
            HTTP_IDEMPOTENCY_KEY="owner-map-key"
        )
        mapping_id = res.data["data"]["id"]

        # Other user cannot view or delete
        self.client.force_authenticate(user=self.other_user)

        get_res = self.client.get(f"/api/mappings/{mapping_id}/")
        self.assertEqual(get_res.status_code, status.HTTP_403_FORBIDDEN)

        del_res = self.client.delete(f"/api/mappings/{mapping_id}/")
        self.assertEqual(del_res.status_code, status.HTTP_403_FORBIDDEN)
