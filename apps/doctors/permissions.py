from rest_framework import permissions


class IsDoctorCreatorOrReadOnly(permissions.BasePermission):
    """
    Object-level permission allowing any authenticated user to view doctors,
    but restricting updates and deletions strictly to the doctor's creator.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # Safe methods (GET, HEAD, OPTIONS) allowed for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        # Mutating methods (PUT, PATCH, DELETE) allowed only for creator
        return obj.created_by_id == request.user.id
