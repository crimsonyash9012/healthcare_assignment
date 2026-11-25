from rest_framework import permissions


class IsPatientCreator(permissions.BasePermission):
    """
    Object-level permission ensuring only the user who created
    the patient record can view, update, or delete it.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # Patient creator only
        return obj.created_by_id == request.user.id
