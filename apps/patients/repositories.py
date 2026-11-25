from typing import Optional, Tuple
from django.db.models import QuerySet, F
from django.utils import timezone
from apps.patients.models import Patient


class PatientRepository:
    """
    Repository layer abstracting persistence and Django ORM queries for the Patient domain.
    Flow: Service -> Repository -> ORM -> PostgreSQL
    """

    @staticmethod
    def get_by_id(patient_id: int) -> Optional[Patient]:
        """Fetch a single patient by primary key."""
        return Patient.objects.filter(id=patient_id).first()

    @staticmethod
    def get_by_user(user_id: int) -> QuerySet[Patient]:
        """Retrieve all patients created by a specific user."""
        return Patient.objects.filter(created_by_id=user_id)

    @staticmethod
    def create(**data) -> Patient:
        """Create and persist a new Patient instance."""
        return Patient.objects.create(**data)

    @staticmethod
    def update_with_version(
        patient_id: int,
        expected_version: int,
        **update_fields
    ) -> Tuple[bool, Optional[Patient]]:
        """
        Executes atomic optimistic locking update.
        Matches id and expected_version, and increments version atomically by 1.
        Returns:
            Tuple[success: bool, updated_patient: Optional[Patient]]
        """
        update_fields['updated_at'] = timezone.now()
        rows_updated = Patient.objects.filter(
            id=patient_id,
            version=expected_version
        ).update(
            version=F('version') + 1,
            **update_fields
        )

        if rows_updated == 1:
            return True, Patient.objects.get(id=patient_id)
        return False, None

    @staticmethod
    def delete(patient_id: int) -> bool:
        """Deletes a patient record by ID."""
        deleted_count, _ = Patient.objects.filter(id=patient_id).delete()
        return deleted_count > 0
