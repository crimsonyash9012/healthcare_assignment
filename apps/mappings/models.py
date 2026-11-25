from django.db import models
from apps.patients.models import Patient
from apps.doctors.models import Doctor


class PatientDoctorMapping(models.Model):
    """
    Junction table implementing a many-to-many relationship between patients and doctors.
    Enforces uniqueness so a doctor cannot be assigned multiple times to the same patient.
    """
    id = models.BigAutoField(primary_key=True)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="doctor_mappings"
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="patient_mappings"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "patient_doctor_mappings"
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "doctor"],
                name="unique_patient_doctor"
            )
        ]
        indexes = [
            models.Index(fields=["patient", "doctor"]),
            models.Index(fields=["assigned_at"]),
        ]

    def __str__(self):
        return f"Patient #{self.patient_id} <-> Dr. #{self.doctor_id}"
