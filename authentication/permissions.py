from rest_framework.permissions import BasePermission

from .models import UserProfile, UserRole


class IsAdminRole(BasePermission):
    """Permite apenas utilizadores autenticados com perfil de ADMIN."""

    message = "Apenas administradores podem realizar esta operação."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        try:
            return user.profile.role == UserRole.ADMIN
        except UserProfile.DoesNotExist:
            return False
