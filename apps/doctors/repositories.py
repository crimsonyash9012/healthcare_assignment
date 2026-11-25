from typing import Optional, Tuple
from django.db.models import QuerySet, F
from django.utils import timezone
from apps.doctors.models import Doctor


class DoctorRepository:
    """Repository layer abstracting persistence and queries for the Doctor domain."""

    @staticmethod
    def get_by_id(doctor_id: int) -> Optional[Doctor]:
        return Doctor.objects.filter(id=doctor_id).first()

    @staticmethod
    def get_by_email(email: str) -> Optional[Doctor]:
        return Doctor.objects.filter(email=email.lower()).first()

    @staticmethod
    def list_all() -> QuerySet[Doctor]:
        return Doctor.objects.all()

    @staticmethod
    def create(**data) -> Doctor:
        if 'email' in data:
            data['email'] = data['email'].lower()
        return Doctor.objects.create(**data)

    @staticmethod
    def update_with_version(
        doctor_id: int,
        expected_version: int,
        **update_fields
    ) -> Tuple[bool, Optional[Doctor]]:
        if 'email' in update_fields:
            update_fields['email'] = update_fields['email'].lower()

        update_fields['updated_at'] = timezone.now()
        rows_updated = Doctor.objects.filter(
            id=doctor_id,
            version=expected_version
        ).update(
            version=F('version') + 1,
            **update_fields
        )

        if rows_updated == 1:
            return True, Doctor.objects.get(id=doctor_id)
        return False, None

    @staticmethod
    def delete(doctor_id: int) -> bool:
        deleted_count, _ = Doctor.objects.filter(id=doctor_id).delete()
        return deleted_count > 0
