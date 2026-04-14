from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """Custom permission to only allow admin users."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsOwnerOrAdmin(permissions.BasePermission):
    """Custom permission to only allow owners of an object or admins."""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.user == request.user


class IsBeauticianOwner(permissions.BasePermission):
    """Custom permission to only allow beautician owners."""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if hasattr(obj, 'beautician'):
            return obj.beautician.user == request.user
        if hasattr(obj, 'user'):
            from beauticians.models import Beautician
            try:
                beautician = Beautician.objects.get(user=request.user)
                return obj.beautician == beautician
            except Beautician.DoesNotExist:
                return False
        return False


class ReadOnly(permissions.BasePermission):
    """Custom permission to only allow read-only access."""
    
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
