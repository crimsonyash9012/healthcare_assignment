from django.test import TestCase
from datetime import date
from apps.accounts.models import User
from apps.patients.services import PatientService
from apps.doctors.services import DoctorService
from apps.mappings.services import MappingService
from common.exceptions import (
    AuthorizationError,
    OptimisticLockError,
    ConflictError,
    ResourceNotFoundError
)


class ServiceLayerTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email="user1@example.com", name="User One", password="password123")
        self.user2 = User.objects.create_user(email="user2@example.com", name="User Two", password="password123")

    def test_patient_service_creator_authorization(self):
        patient = PatientService.create_patient(
            user=self.user1,
            data={
                "name": "Jane Doe",
                "date_of_birth": date(1995, 1, 1),
                "gender": "Female"
            }
        )
        self.assertEqual(patient.created_by_id, self.user1.id)

        # User 1 can view
        retrieved = PatientService.get_patient(user=self.user1, patient_id=patient.id)
        self.assertEqual(retrieved.id, patient.id)

        # User 2 cannot view (Creator only)
        with self.assertRaises(AuthorizationError):
            PatientService.get_patient(user=self.user2, patient_id=patient.id)

        # User 2 cannot update
        with self.assertRaises(AuthorizationError):
            PatientService.update_patient(
                user=self.user2,
                patient_id=patient.id,
                data={"name": "Tampered Name"},
                expected_version=1
            )

    def test_patient_service_optimistic_lock_error(self):
        patient = PatientService.create_patient(
            user=self.user1,
            data={
                "name": "Target Patient",
                "date_of_birth": date(1990, 8, 15),
                "gender": "Male"
            }
        )
        # Update 1 succeeds
        updated1 = PatientService.update_patient(
            user=self.user1,
            patient_id=patient.id,
            data={"name": "First Update"},
            expected_version=1
        )
        self.assertEqual(updated1.version, 2)

        # Concurrent update with stale version 1 must raise OptimisticLockError
        with self.assertRaises(OptimisticLockError):
            PatientService.update_patient(
                user=self.user1,
                patient_id=patient.id,
                data={"name": "Stale Update"},
                expected_version=1
            )

    def test_mapping_service_creator_enforcement(self):
        patient = PatientService.create_patient(
            user=self.user1,
            data={"name": "P1", "date_of_birth": date(2000, 1, 1), "gender": "Other"}
        )
        doctor = DoctorService.create_doctor(
            user=self.user2,
            data={"name": "Dr. Strange", "specialization": "Surgery", "email": "strange@marvel.com"}
        )

        # User 2 cannot assign a doctor to User 1's patient
        with self.assertRaises(AuthorizationError):
            MappingService.assign_doctor(user=self.user2, patient_id=patient.id, doctor_id=doctor.id)

        # User 1 (patient creator) can assign
        mapping = MappingService.assign_doctor(user=self.user1, patient_id=patient.id, doctor_id=doctor.id)
        self.assertEqual(mapping.patient_id, patient.id)

        # Duplicate assignment raises ConflictError
        with self.assertRaises(ConflictError):
            MappingService.assign_doctor(user=self.user1, patient_id=patient.id, doctor_id=doctor.id)
