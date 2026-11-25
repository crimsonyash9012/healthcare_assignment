from typing import Optional, Dict, Any
from django.db import transaction
from django.db.models import QuerySet

from apps.doctors.models import Doctor
from apps.doctors.repositories import DoctorRepository
from common.exceptions import (
    ResourceNotFoundError,
    AuthorizationError,
    OptimisticLockError,
    ConflictError
)
from apps.audit.services import AuditService


class DoctorService:
    """Service layer managing Doctor business operations, optimistic concurrency, and audit logs."""

    @staticmethod
    def list_doctors(user) -> QuerySet[Doctor]:
        AuditService.log_action(user=user, action="LIST", resource_type="Doctor")
        return DoctorRepository.list_all()

    @staticmethod
    def get_doctor(user, doctor_id: int) -> Doctor:
        doctor = DoctorRepository.get_by_id(doctor_id)
        if not doctor:
            raise ResourceNotFoundError(f"Doctor with ID {doctor_id} does not exist.")
        AuditService.log_action(user=user, action="VIEW", resource_type="Doctor", resource_id=doctor.id)
        return doctor

    @staticmethod
    @transaction.atomic
    def create_doctor(user, data: Dict[str, Any]) -> Doctor:
        email = data.get('email', '').lower()
        if DoctorRepository.get_by_email(email):
            raise ConflictError(f"A doctor with email '{email}' already exists.")

        doctor = DoctorRepository.create(created_by=user, **data)
        AuditService.log_action(
            user=user,
            action="CREATE",
            resource_type="Doctor",
            resource_id=doctor.id,
            details=f"Created Dr. {doctor.name}"
        )
        return doctor

    @staticmethod
    @transaction.atomic
    def update_doctor(
        user,
        doctor_id: int,
        data: Dict[str, Any],
        expected_version: int
    ) -> Doctor:
        doctor = DoctorRepository.get_by_id(doctor_id)
        if not doctor:
            raise ResourceNotFoundError(f"Doctor with ID {doctor_id} does not exist.")

        if doctor.created_by_id != user.id:
            raise AuthorizationError("You do not have permission to modify this doctor profile.")

        success, updated_doctor = DoctorRepository.update_with_version(
            doctor_id=doctor_id,
            expected_version=expected_version,
            **data
        )

        if not success:
            raise OptimisticLockError(
                f"Doctor profile was updated concurrently. Expected version {expected_version}, but version has advanced."
            )

        AuditService.log_action(
            user=user,
            action="UPDATE",
            resource_type="Doctor",
            resource_id=doctor.id,
            details=f"Updated Dr. {doctor.name} to version {updated_doctor.version}"
        )
        return updated_doctor

    @staticmethod
    @transaction.atomic
    def delete_doctor(user, doctor_id: int) -> None:
        doctor = DoctorRepository.get_by_id(doctor_id)
        if not doctor:
            raise ResourceNotFoundError(f"Doctor with ID {doctor_id} does not exist.")

        if doctor.created_by_id != user.id:
            raise AuthorizationError("You do not have permission to delete this doctor profile.")

        DoctorRepository.delete(doctor_id)
        AuditService.log_action(
            user=user,
            action="DELETE",
            resource_type="Doctor",
            resource_id=doctor_id,
            details=f"Deleted Dr. {doctor.name}"
        )
