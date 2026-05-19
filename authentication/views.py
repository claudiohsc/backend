import logging

from django.contrib.auth import get_user_model
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    EmailLoginSerializer,
    GoogleAuthSerializer,
    LogoutInputSerializer,
    RegisterSerializer,
    TokenRefreshInputSerializer,
    UserSerializer,
)
from .services import (
    GoogleAuthService,
    InvalidCredentialsException,
    InvalidGoogleTokenException,
    LocalAuthService,
)

logger = logging.getLogger(__name__)
User = get_user_model()


def get_tokens_for_user(user) -> dict:
    """Gera um par de tokens JWT (access + refresh) para o utilizador."""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


_AUTH_SUCCESS_EXAMPLE_NEW = OpenApiExample(
    name="Novo utilizador (201)",
    summary="Primeiro login — conta criada",
    value={
        "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "is_new_user": True,
        "user": {
            "id": 1,
            "email": "user@gmail.com",
            "name": "Nome Completo",
            "avatar_url": "https://lh3.googleusercontent.com/...",
            "is_new_user": True,
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-01T12:00:00Z",
        },
    },
    response_only=True,
    status_codes=["201"],
)

_AUTH_SUCCESS_EXAMPLE_EXISTING = OpenApiExample(
    name="Utilizador existente (200)",
    summary="Login recorrente",
    value={
        "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "is_new_user": False,
        "user": {
            "id": 1,
            "email": "user@gmail.com",
            "name": "Nome Completo",
            "avatar_url": "https://lh3.googleusercontent.com/...",
            "is_new_user": False,
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-15T08:30:00Z",
        },
    },
    response_only=True,
    status_codes=["200"],
)


# ─── Views ────────────────────────────────────────────────────────────────────


class GoogleLoginView(APIView):
    """Login com Google OAuth 2.0."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Auth"],
        summary="Login com Google",
        description=(
            "Recebe o `id_token` retornado pelo Google Sign-In e autentica o utilizador.\n\n"
            "**Fluxo:**\n"
            "1. O frontend inicia o Google Sign-In\n"
            "2. O Google retorna um `credential` (id_token JWT)\n"
            "3. O frontend envia esse token para este endpoint\n"
            "4. O backend verifica junto ao Google e retorna tokens JWT + dados do user\n\n"
            "**Comportamento:**\n"
            "- Primeiro login → cria conta e retorna `201 Created` com `is_new_user: true`\n"
            "- Login recorrente → retorna `200 OK` com `is_new_user: false`\n"
            "- Email já existe sem Google → vincula a conta ao Google e retorna `200 OK`"
        ),
        request=GoogleAuthSerializer,
        responses={
            200: OpenApiResponse(
                description="Login bem-sucedido — utilizador existente",
                examples=[_AUTH_SUCCESS_EXAMPLE_EXISTING],
            ),
            201: OpenApiResponse(
                description="Login bem-sucedido — novo utilizador criado",
                examples=[_AUTH_SUCCESS_EXAMPLE_NEW],
            ),
            400: OpenApiResponse(
                description="Pedido inválido — `id_token` em falta ou malformado",
                examples=[
                    OpenApiExample(
                        name="Token em falta",
                        value={
                            "error": "id_token é obrigatório.",
                            "details": {"id_token": ["This field is required."]},
                        },
                        response_only=True,
                        status_codes=["400"],
                    )
                ],
            ),
            401: OpenApiResponse(
                description="Token Google inválido ou expirado",
                examples=[
                    OpenApiExample(
                        name="Token inválido",
                        value={
                            "error": "Token Google inválido ou expirado.",
                            "details": "Token invalid: ...",
                        },
                        response_only=True,
                        status_codes=["401"],
                    )
                ],
            ),
            500: OpenApiResponse(description="Erro interno do servidor"),
        },
        examples=[
            OpenApiExample(
                name="Payload de login",
                summary="Enviar id_token do Google",
                value={"id_token": "<google-id-token-jwt>"},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"error": "id_token é obrigatório.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        id_token_str = serializer.validated_data["id_token"]

        try:
            user, is_new_user = GoogleAuthService.authenticate_or_create_user(id_token_str)
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


class RegisterView(APIView):
    """Cadastro com e-mail e senha."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Auth"],
        summary="Cadastro com e-mail e senha",
        description=(
            "Cria uma nova conta com e-mail e senha local e retorna tokens JWT.\n\n"
            "**Fluxo:**\n"
            "1. Frontend envia `email`, `password` e `name`\n"
            "2. Backend valida (e-mail único, senha forte) e cria o utilizador\n"
            "3. Backend dispara e-mail de boas-vindas (não-bloqueante)\n"
            "4. Backend retorna tokens JWT + dados do utilizador\n\n"
            "**Validações da senha:** mínimo 8 caracteres + regras de Django "
            "(`UserAttributeSimilarity`, `MinimumLength`, `CommonPassword`, `NumericPassword`)."
        ),
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(
                description="Conta criada com sucesso",
                examples=[
                    OpenApiExample(
                        name="Cadastro bem-sucedido",
                        value={
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "is_new_user": True,
                            "user": {
                                "id": 1,
                                "email": "user@example.com",
                                "name": "Nome Completo",
                                "avatar_url": None,
                                "is_new_user": True,
                                "created_at": "2024-01-01T12:00:00Z",
                                "updated_at": "2024-01-01T12:00:00Z",
                            },
                        },
                        response_only=True,
                        status_codes=["201"],
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Payload inválido (e-mail duplicado, senha fraca, etc.)",
                examples=[
                    OpenApiExample(
                        name="E-mail já cadastrado",
                        value={
                            "error": "Dados inválidos.",
                            "details": {"email": ["E-mail já cadastrado."]},
                        },
                        response_only=True,
                        status_codes=["400"],
                    )
                ],
            ),
        },
        examples=[
            OpenApiExample(
                name="Payload de cadastro",
                value={
                    "email": "user@example.com",
                    "password": "SenhaSegura123",
                    "name": "Nome Completo",
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Dados inválidos.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = LocalAuthService.register_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            name=serializer.validated_data["name"],
        )

        tokens = get_tokens_for_user(user)
        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "is_new_user": True,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Login com e-mail e senha."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Auth"],
        summary="Login com e-mail e senha",
        description=(
            "Autentica um utilizador com e-mail e senha e retorna tokens JWT.\n\n"
            "Retorna `401 Unauthorized` para e-mail desconhecido, senha incorreta, "
            "ou contas criadas apenas via Google (sem senha local)."
        ),
        request=EmailLoginSerializer,
        responses={
            200: OpenApiResponse(
                description="Login bem-sucedido",
                examples=[
                    OpenApiExample(
                        name="Login OK",
                        value={
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "is_new_user": False,
                            "user": {
                                "id": 1,
                                "email": "user@example.com",
                                "name": "Nome Completo",
                                "avatar_url": None,
                                "is_new_user": False,
                                "created_at": "2024-01-01T12:00:00Z",
                                "updated_at": "2024-01-15T08:30:00Z",
                            },
                        },
                        response_only=True,
                        status_codes=["200"],
                    )
                ],
            ),
            400: OpenApiResponse(description="Payload inválido (campos faltando)"),
            401: OpenApiResponse(
                description="E-mail ou senha inválidos",
                examples=[
                    OpenApiExample(
                        name="Credenciais inválidas",
                        value={"error": "E-mail ou senha inválidos."},
                        response_only=True,
                        status_codes=["401"],
                    )
                ],
            ),
        },
        examples=[
            OpenApiExample(
                name="Payload de login",
                value={"email": "user@example.com", "password": "SenhaSegura123"},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = EmailLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Dados inválidos.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = LocalAuthService.authenticate_user(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
            )
        except InvalidCredentialsException as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = get_tokens_for_user(user)
        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "is_new_user": False,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(APIView):
    """Renovação do access token."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Auth"],
        summary="Renovar access token",
        description=(
            "Usa o `refresh` token para gerar um novo `access` token.\n\n"
            "O `refresh` token tem validade de **7 dias**. O `access` token gerado tem validade de **1 hora**.\n\n"
            "> ⚠️ Com `ROTATE_REFRESH_TOKENS = True`, o refresh token antigo é invalidado e um novo é gerado."
        ),
        request=TokenRefreshInputSerializer,
        responses={
            200: OpenApiResponse(
                description="Novo access token gerado",
                examples=[
                    OpenApiExample(
                        name="Token renovado",
                        value={"access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
                        response_only=True,
                        status_codes=["200"],
                    )
                ],
            ),
            400: OpenApiResponse(description="Campo `refresh` em falta"),
            401: OpenApiResponse(description="Refresh token inválido ou expirado"),
        },
        examples=[
            OpenApiExample(
                name="Payload",
                value={"refresh": "<refresh-token-jwt>"},
                request_only=True,
            )
        ],
    )
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
    """Terminar sessão."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Logout",
        description=(
            "Invalida o `refresh` token, terminando a sessão do utilizador.\n\n"
            "O token é adicionado à **blacklist** do SimpleJWT e não pode mais ser usado.\n\n"
            "**Requer:** `Authorization: Bearer <access_token>` no header."
        ),
        request=LogoutInputSerializer,
        responses={
            200: OpenApiResponse(
                description="Sessão terminada",
                examples=[
                    OpenApiExample(
                        name="Sucesso",
                        value={"message": "Sessão terminada com sucesso."},
                        response_only=True,
                        status_codes=["200"],
                    )
                ],
            ),
            400: OpenApiResponse(description="Campo `refresh` em falta ou token já expirado"),
            401: OpenApiResponse(description="Não autenticado — access token inválido ou em falta"),
        },
        examples=[
            OpenApiExample(
                name="Payload",
                value={"refresh": "<refresh-token-jwt>"},
                request_only=True,
            )
        ],
    )
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
    """Dados do utilizador autenticado."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Users"],
        summary="Perfil do utilizador autenticado",
        description=(
            "Retorna os dados do utilizador associado ao JWT enviado no header.\n\n"
            "**Requer:** `Authorization: Bearer <access_token>` no header.\n\n"
            "Use este endpoint para:\n"
            "- Preencher o estado global do utilizador no frontend após login\n"
            "- Exibir nome e avatar no header da plataforma\n"
            "- Verificar se o utilizador está activo"
        ),
        responses={
            200: OpenApiResponse(
                response=UserSerializer,
                description="Dados do utilizador",
                examples=[
                    OpenApiExample(
                        name="Utilizador autenticado",
                        value={
                            "id": 1,
                            "email": "user@gmail.com",
                            "name": "Nome Completo",
                            "avatar_url": "https://lh3.googleusercontent.com/...",
                            "is_new_user": False,
                            "created_at": "2024-01-01T12:00:00Z",
                            "updated_at": "2024-01-15T08:30:00Z",
                        },
                        response_only=True,
                        status_codes=["200"],
                    )
                ],
            ),
            401: OpenApiResponse(description="Não autenticado — access token inválido ou em falta"),
        },
    )
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
