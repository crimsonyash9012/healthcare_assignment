from rest_framework import serializers
from apps.patients.models import Patient


class PatientSerializer(serializers.ModelSerializer):
    """Full patient representation with version and timestamps."""
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id',
            'created_by',
            'created_by_name',
            'name',
            'date_of_birth',
            'gender',
            'phone',
            'address',
            'medical_history',
            'version',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'version', 'created_at', 'updated_at']


class PatientCreateSerializer(serializers.ModelSerializer):
    """Payload validation for creating a new patient record."""
    class Meta:
        model = Patient
        fields = [
            'name',
            'date_of_birth',
            'gender',
            'phone',
            'address',
            'medical_history',
        ]


class PatientUpdateSerializer(serializers.ModelSerializer):
    """Payload validation for updating a patient record with optimistic locking."""
    version = serializers.IntegerField(
        required=True,
        help_text="Expected current version counter for optimistic locking."
    )

    class Meta:
        model = Patient
        fields = [
            'name',
            'date_of_birth',
            'gender',
            'phone',
            'address',
            'medical_history',
            'version',
        ]
