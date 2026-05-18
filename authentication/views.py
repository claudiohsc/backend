import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import GoogleAuthSerializer, UserSerializer
from .services import GoogleAuthService, InvalidGoogleTokenException

logger = logging.getLogger(__name__)
User = get_user_model()


def get_tokens_for_user(user) -> dict:
    """
    Gera um par de tokens JWT (access + refresh) para o utilizador.
    Usado após autenticação bem-sucedida.
    """
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class GoogleLoginView(APIView):
    """
    Endpoint de autenticação com Google OAuth 2.0.

    Recebe o `id_token` do Google Sign-In (enviado pelo frontend),
    verifica junto ao Google, e cria ou autentica o utilizador.

    POST /api/auth/google/

    Request Body:
        {
            "id_token": "<token JWT retornado pelo Google>"
        }

    Response (200 OK - utilizador existente):
        {
            "access": "<JWT>",
            "refresh": "<JWT>",
            "is_new_user": false,
            "user": {
                "id": 1,
                "email": "user@example.com",
                "name": "Nome Completo",
                "avatar_url": "https://...",
                "is_new_user": false,
                "created_at": "...",
                "updated_at": "..."
            }
        }

    Response (201 Created - novo utilizador):
        {
            "access": "<JWT>",
            "refresh": "<JWT>",
            "is_new_user": true,
            "user": { ... }
        }

    Response (400 Bad Request):
        { "error": "id_token é obrigatório." }

    Response (401 Unauthorized):
        { "error": "Token Google inválido ou expirado." }
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # Não requer autenticação prévia

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"error": "id_token é obrigatório.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        id_token_str = serializer.validated_data["id_token"]

        try:
            user, is_new_user = GoogleAuthService.authenticate_or_create_user(
                id_token_str
            )
        except InvalidGoogleTokenException as e:
            logger.warning(f"Tentativa de login com token inválido: {e}")
            return Response(
                {"error": "Token Google inválido ou expirado.", "details": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except Exception as e:
            logger.error(f"Erro inesperado no login com Google: {e}", exc_info=True)
            return Response(
                {"error": "Erro interno no servidor. Tente novamente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        tokens = get_tokens_for_user(user)
        user_data = UserSerializer(user).data
        response_status = status.HTTP_201_CREATED if is_new_user else status.HTTP_200_OK

        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "is_new_user": is_new_user,
                "user": user_data,
            },
            status=response_status,
        )


class TokenRefreshView(APIView):
    """
    Renova o access token usando o refresh token.

    POST /api/auth/token/refresh/

    Request Body:
        { "refresh": "<refresh token JWT>" }

    Response (200 OK):
        { "access": "<novo access token JWT>" }
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"error": "refresh token é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            new_access = str(token.access_token)
            return Response({"access": new_access}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.warning(f"Refresh token inválido: {e}")
            return Response(
                {"error": "Refresh token inválido ou expirado."},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class LogoutView(APIView):
    """
    Invalida o refresh token (blacklist), terminando a sessão.

    POST /api/auth/logout/

    Headers:
        Authorization: Bearer <access token>

    Request Body:
        { "refresh": "<refresh token>" }

    Response (200 OK):
        { "message": "Sessão terminada com sucesso." }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"error": "refresh token é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"message": "Sessão terminada com sucesso."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.warning(f"Erro ao fazer logout: {e}")
            return Response(
                {"error": "Token inválido ou já expirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MeView(APIView):
    """
    Retorna os dados do utilizador autenticado.

    GET /api/auth/me/

    Headers:
        Authorization: Bearer <access token>

    Response (200 OK):
        {
            "id": 1,
            "email": "user@example.com",
            "name": "Nome Completo",
            "avatar_url": "https://...",
            "is_new_user": false,
            "created_at": "...",
            "updated_at": "..."
        }

    # TODO (Frontend): Usar esta resposta para preencher o estado global do utilizador
    # e exibir nome/avatar no header da plataforma.
    # Exemplo de uso no header:
    #
    # if (user) {
    #   return (
    #     <div className="user-header">
    #       <img src={user.avatar_url} alt={user.name} />
    #       <span>{user.name}</span>
    #       <button onClick={handleLogout}>Sair</button>
    #     </div>
    #   )
    # } else {
    #   return <GoogleLoginButton />
    # }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
