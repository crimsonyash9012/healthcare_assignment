from rest_framework import permissions


class IsMappingPatientOwner(permissions.BasePermission):
    """
    Object-level permission ensuring only the creator of the associated patient
    can view, create, or delete the patient-doctor assignment.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # Patient creator only
        return obj.patient.created_by_id == request.user.id
