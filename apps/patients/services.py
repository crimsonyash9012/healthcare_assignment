from typing import Optional, Dict, Any
from django.db import transaction
from django.db.models import QuerySet

from apps.patients.models import Patient
from apps.patients.repositories import PatientRepository
from common.exceptions import (
    ResourceNotFoundError,
    AuthorizationError,
    OptimisticLockError
)
from apps.audit.services import AuditService


class PatientService:
    """
    Service layer for Patient business logic, authorization enforcement,
    atomic transactions, optimistic locking, and audit log tracking.
    """

    @staticmethod
    def list_patients(user) -> QuerySet[Patient]:
        """
        List all patients created by the authenticated user.
        Patient creator only.
        """
        AuditService.log_action(
            user=user,
            action="LIST",
            resource_type="Patient",
            details="Listed creator patient records"
        )
        return PatientRepository.get_by_user(user.id)

    @staticmethod
    def get_patient(user, patient_id: int) -> Patient:
        """
        Retrieve a single patient record, ensuring object-level creator authorization.
        """
        patient = PatientRepository.get_by_id(patient_id)
        if not patient:
            raise ResourceNotFoundError(f"Patient with ID {patient_id} does not exist.")

        if patient.created_by_id != user.id:
            raise AuthorizationError("You do not have permission to view this patient record.")

        AuditService.log_action(
            user=user,
            action="VIEW",
            resource_type="Patient",
            resource_id=patient.id,
            details=f"Viewed patient {patient.name}"
        )
        return patient

    @staticmethod
    @transaction.atomic
    def create_patient(user, data: Dict[str, Any]) -> Patient:
        """
        Create a new patient record within an atomic database transaction.
        """
        patient = PatientRepository.create(created_by=user, **data)

        AuditService.log_action(
            user=user,
            action="CREATE",
            resource_type="Patient",
            resource_id=patient.id,
            details=f"Created patient {patient.name}"
        )
        return patient

    @staticmethod
    @transaction.atomic
    def update_patient(
        user,
        patient_id: int,
        data: Dict[str, Any],
        expected_version: int
    ) -> Patient:
        """
        Update an existing patient using optimistic locking to prevent lost updates.
        Raises OptimisticLockError if version mismatch occurs.
        """
        patient = PatientRepository.get_by_id(patient_id)
        if not patient:
            raise ResourceNotFoundError(f"Patient with ID {patient_id} does not exist.")

        if patient.created_by_id != user.id:
            raise AuthorizationError("You do not have permission to update this patient record.")

        success, updated_patient = PatientRepository.update_with_version(
            patient_id=patient_id,
            expected_version=expected_version,
            **data
        )

        if not success:
            raise OptimisticLockError(
                f"Patient record was modified concurrently. Expected version {expected_version}, but resource version has advanced."
            )

        AuditService.log_action(
            user=user,
            action="UPDATE",
            resource_type="Patient",
            resource_id=patient.id,
            details=f"Updated patient {patient.name} to version {updated_patient.version}"
        )
        return updated_patient

    @staticmethod
    @transaction.atomic
    def delete_patient(user, patient_id: int) -> None:
        """
        Delete a patient record, enforcing creator authorization.
        """
        patient = PatientRepository.get_by_id(patient_id)
        if not patient:
            raise ResourceNotFoundError(f"Patient with ID {patient_id} does not exist.")

        if patient.created_by_id != user.id:
            raise AuthorizationError("You do not have permission to delete this patient record.")

        PatientRepository.delete(patient_id)

        AuditService.log_action(
            user=user,
            action="DELETE",
            resource_type="Patient",
            resource_id=patient_id,
            details=f"Deleted patient {patient.name}"
        )
