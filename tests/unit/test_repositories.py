from django.test import TestCase
from datetime import date
from apps.accounts.models import User
from apps.patients.repositories import PatientRepository
from apps.doctors.repositories import DoctorRepository
from apps.mappings.repositories import MappingRepository


class RepositoryLayerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="repo.user@example.com",
            name="Repo User",
            password="StrongPassword123!"
        )

    def test_patient_repository_create_and_versioning(self):
        patient = PatientRepository.create(
            created_by=self.user,
            name="Alice Smith",
            date_of_birth=date(1990, 5, 12),
            gender="Female",
            phone="1234567890"
        )
        self.assertIsNotNone(patient.id)
        self.assertEqual(patient.version, 1)

        # Successful optimistic update with matching version
        success, updated = PatientRepository.update_with_version(
            patient_id=patient.id,
            expected_version=1,
            name="Alice Johnson"
        )
        self.assertTrue(success)
        self.assertEqual(updated.name, "Alice Johnson")
        self.assertEqual(updated.version, 2)

        # Stale update attempt with old version must fail
        stale_success, _ = PatientRepository.update_with_version(
            patient_id=patient.id,
            expected_version=1,  # Version is now 2
            name="Alice Conflict"
        )
        self.assertFalse(stale_success)

    def test_doctor_repository(self):
        doctor = DoctorRepository.create(
            created_by=self.user,
            name="Gregory House",
            specialization="Diagnostic Medicine",
            email="house@princeton.edu",
            experience_years=20
        )
        self.assertIsNotNone(doctor.id)
        self.assertEqual(doctor.version, 1)

        fetched = DoctorRepository.get_by_email("house@princeton.edu")
        self.assertEqual(fetched.id, doctor.id)

    def test_mapping_repository(self):
        patient = PatientRepository.create(
            created_by=self.user,
            name="Bob Brown",
            date_of_birth=date(1985, 3, 22),
            gender="Male"
        )
        doctor = DoctorRepository.create(
            created_by=self.user,
            name="James Wilson",
            specialization="Oncology",
            email="wilson@princeton.edu"
        )

        mapping = MappingRepository.create(patient=patient, doctor=doctor)
        self.assertIsNotNone(mapping.id)

        user_mappings = MappingRepository.list_by_user(self.user.id)
        self.assertEqual(user_mappings.count(), 1)
        self.assertEqual(user_mappings.first().doctor.id, doctor.id)
