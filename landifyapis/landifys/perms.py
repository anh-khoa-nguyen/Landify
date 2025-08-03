from rest_framework import permissions
from landifys.models import User

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == User.Role.ADMIN

class IsAdminOrForbidden(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.ADMIN

class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        return obj.resident == request.user

class IsIdentityVerified(permissions.BasePermission):
    message = 'Your identity must be verified to perform this action.'

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_id_card_verified and request.user.is_phone_verified