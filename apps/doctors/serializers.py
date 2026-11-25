from rest_framework import serializers
from apps.doctors.models import Doctor


class DoctorSerializer(serializers.ModelSerializer):
    """Full doctor representation including version counter."""
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)

    class Meta:
        model = Doctor
        fields = [
            'id',
            'created_by',
            'created_by_name',
            'name',
            'specialization',
            'email',
            'phone',
            'qualifications',
            'experience_years',
            'version',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'version', 'created_at', 'updated_at']


class DoctorCreateSerializer(serializers.ModelSerializer):
    """Payload validation for adding a doctor."""
    class Meta:
        model = Doctor
        fields = [
            'name',
            'specialization',
            'email',
            'phone',
            'qualifications',
            'experience_years',
        ]

    def validate_email(self, value):
        normalized = value.lower()
        if Doctor.objects.filter(email=normalized).exists():
            raise serializers.ValidationError("A doctor with this email is already registered.")
        return normalized


class DoctorUpdateSerializer(serializers.ModelSerializer):
    """Payload validation for updating doctor with optimistic locking."""
    version = serializers.IntegerField(
        required=True,
        help_text="Expected current version counter for optimistic locking."
    )

    class Meta:
        model = Doctor
        fields = [
            'name',
            'specialization',
            'email',
            'phone',
            'qualifications',
            'experience_years',
            'version',
        ]

    def validate_email(self, value):
        normalized = value.lower()
        # Ensure email uniqueness if changed
        if self.instance and self.instance.email == normalized:
            return normalized
        if Doctor.objects.filter(email=normalized).exclude(id=getattr(self.instance, 'id', None)).exists():
            raise serializers.ValidationError("A doctor with this email is already registered.")
        return normalized
