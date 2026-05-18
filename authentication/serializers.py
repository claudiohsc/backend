from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer completo do utilizador para respostas da API.
    Expõe os campos relevantes sem dados sensíveis.
    """

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
    """
    Serializer para validar o payload enviado pelo frontend no login com Google.
    O frontend deve enviar o id_token retornado pelo Google Sign-In.
    """

    id_token = serializers.CharField(
        required=True,
        help_text="Token de ID retornado pelo Google Sign-In (credencial JWT).",
    )


class AuthResponseSerializer(serializers.Serializer):
    """
    Serializer de documentação para a resposta do endpoint de autenticação.
    Não usado diretamente, mas serve como contrato da API para o frontend.

    Resposta esperada:
    {
        "access": "<JWT access token>",
        "refresh": "<JWT refresh token>",
        "user": { ...UserSerializer fields... },
        "is_new_user": true/false
    }
    """

    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)
    is_new_user = serializers.BooleanField(read_only=True)
