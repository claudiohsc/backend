from rest_framework import permissions


class IsStaffOrSuperuser(permissions.BasePermission):
    """Permite acesso apenas a utilizadores administradores (Staff/Superuser)."""

    message = "Acesso negado. Apenas administradores podem aceder a este recurso."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )
