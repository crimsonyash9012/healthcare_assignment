from typing import Optional
from django.db.models import QuerySet
from apps.mappings.models import PatientDoctorMapping


class MappingRepository:
    """Repository layer abstracting persistence and queries for patient-doctor relationships."""

    @staticmethod
    def get_by_id(mapping_id: int) -> Optional[PatientDoctorMapping]:
        return PatientDoctorMapping.objects.select_related('patient', 'doctor').filter(id=mapping_id).first()

    @staticmethod
    def get_by_patient_and_doctor(patient_id: int, doctor_id: int) -> Optional[PatientDoctorMapping]:
        return PatientDoctorMapping.objects.filter(patient_id=patient_id, doctor_id=doctor_id).first()

    @staticmethod
    def list_by_user(user_id: int) -> QuerySet[PatientDoctorMapping]:
        """List mappings for all patients owned by the specified user."""
        return (
            PatientDoctorMapping.objects.select_related('patient', 'doctor')
            .filter(patient__created_by_id=user_id)
        )

    @staticmethod
    def create(patient, doctor) -> PatientDoctorMapping:
        return PatientDoctorMapping.objects.create(patient=patient, doctor=doctor)

    @staticmethod
    def delete(mapping_id: int) -> bool:
        deleted_count, _ = PatientDoctorMapping.objects.filter(id=mapping_id).delete()
        return deleted_count > 0
