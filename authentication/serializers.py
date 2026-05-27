from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer completo do utilizador para respostas da API."""

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "avatar_url",
            "is_new_user",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class GoogleAuthSerializer(serializers.Serializer):
    """Valida o payload de login com Google."""

    id_token = serializers.CharField(
        required=True,
        help_text="Token de ID retornado pelo Google Sign-In (credencial JWT).",
    )


class AuthResponseSerializer(serializers.Serializer):
    """Contrato da resposta do endpoint de autenticação (documentação)."""

    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)
    is_new_user = serializers.BooleanField(read_only=True)


class TokenRefreshInputSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=True,
        help_text=(
            "Refresh token JWT obtido no login. "
            "Válido por 7 dias. "
            "Após uso, o token antigo é invalidado e um novo é emitido (rotation)."
        ),
    )


class LogoutInputSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=True,
        help_text=(
            "Refresh token JWT a invalidar. "
            "Após este pedido, o token fica na blacklist e não pode mais ser usado."
        ),
    )
