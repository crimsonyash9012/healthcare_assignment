from rest_framework import serializers
from apps.mappings.models import PatientDoctorMapping
from apps.patients.models import Patient
from apps.doctors.models import Doctor


class MappingSerializer(serializers.ModelSerializer):
    """Detailed patient-doctor mapping representation."""
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)
    doctor_specialization = serializers.CharField(source='doctor.specialization', read_only=True)

    class Meta:
        model = PatientDoctorMapping
        fields = [
            'id',
            'patient',
            'patient_name',
            'doctor',
            'doctor_name',
            'doctor_specialization',
            'assigned_at',
        ]
        read_only_fields = ['id', 'assigned_at']


class MappingCreateSerializer(serializers.Serializer):
    """Payload validation for assigning a doctor to a patient."""
    patient_id = serializers.IntegerField(required=True)
    doctor_id = serializers.IntegerField(required=True)

    def validate_patient_id(self, value):
        if not Patient.objects.filter(id=value).exists():
            raise serializers.ValidationError("Patient does not exist.")
        return value

    def validate_doctor_id(self, value):
        if not Doctor.objects.filter(id=value).exists():
            raise serializers.ValidationError("Doctor does not exist.")
        return value
