from django.db import transaction
from django.db.models import QuerySet

from apps.mappings.models import PatientDoctorMapping
from apps.mappings.repositories import MappingRepository
from apps.patients.repositories import PatientRepository
from apps.doctors.repositories import DoctorRepository
from common.exceptions import (
    ResourceNotFoundError,
    AuthorizationError,
    ConflictError
)
from apps.audit.services import AuditService


class MappingService:
    """
    Service layer governing patient-doctor associations, creator ownership checks,
    atomic transactions, and audit records.
    """

    @staticmethod
    def list_mappings(user) -> QuerySet[PatientDoctorMapping]:
        """View mappings: Patient creator only."""
        AuditService.log_action(user=user, action="LIST", resource_type="PatientDoctorMapping")
        return MappingRepository.list_by_user(user.id)

    @staticmethod
    def get_mapping(user, mapping_id: int) -> PatientDoctorMapping:
        mapping = MappingRepository.get_by_id(mapping_id)
        if not mapping:
            raise ResourceNotFoundError(f"Mapping with ID {mapping_id} does not exist.")

        if mapping.patient.created_by_id != user.id:
            raise AuthorizationError("You do not have permission to view this mapping.")

        return mapping

    @staticmethod
    @transaction.atomic
    def assign_doctor(user, patient_id: int, doctor_id: int) -> PatientDoctorMapping:
        """
        Assign doctor: Patient creator only.
        Atomic execution prevents double assignment.
        """
        patient = PatientRepository.get_by_id(patient_id)
        if not patient:
            raise ResourceNotFoundError(f"Patient with ID {patient_id} does not exist.")

        # Object-level authorization: Only the patient creator can assign a doctor
        if patient.created_by_id != user.id:
            raise AuthorizationError("Only the creator of the patient can assign a doctor.")

        doctor = DoctorRepository.get_by_id(doctor_id)
        if not doctor:
            raise ResourceNotFoundError(f"Doctor with ID {doctor_id} does not exist.")

        existing = MappingRepository.get_by_patient_and_doctor(patient_id, doctor_id)
        if existing:
            raise ConflictError("This doctor is already assigned to the specified patient.")

        mapping = MappingRepository.create(patient=patient, doctor=doctor)

        AuditService.log_action(
            user=user,
            action="ASSIGN_DOCTOR",
            resource_type="PatientDoctorMapping",
            resource_id=mapping.id,
            details=f"Assigned Dr. {doctor.name} (ID: {doctor.id}) to Patient {patient.name} (ID: {patient.id})"
        )
        return mapping

    @staticmethod
    @transaction.atomic
    def delete_mapping(user, mapping_id: int) -> None:
        """
        Delete mapping: Patient creator only.
        """
        mapping = MappingRepository.get_by_id(mapping_id)
        if not mapping:
            raise ResourceNotFoundError(f"Mapping with ID {mapping_id} does not exist.")

        if mapping.patient.created_by_id != user.id:
            raise AuthorizationError("Only the creator of the patient can remove this doctor assignment.")

        MappingRepository.delete(mapping_id)

        AuditService.log_action(
            user=user,
            action="UNASSIGN_DOCTOR",
            resource_type="PatientDoctorMapping",
            resource_id=mapping_id,
            details=f"Removed mapping between Patient ID {mapping.patient_id} and Doctor ID {mapping.doctor_id}"
        )
