"""
Testes unitários e de integração para o app de autenticação.

Executar com:
    python manage.py test authentication
    ou
    pytest authentication/tests.py -v
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .services import GoogleAuthService, InvalidGoogleTokenException

User = get_user_model()


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_google_payload(
    sub="123456789",
    email="test@example.com",
    name="Test User",
    picture="https://example.com/avatar.jpg",
    email_verified=True,
):
    """Cria um payload simulado do Google para testes."""
    return {
        "sub": sub,
        "email": email,
        "name": name,
        "picture": picture,
        "email_verified": email_verified,
        "aud": "test-client-id.apps.googleusercontent.com",
    }


# ─── Testes do GoogleAuthService ──────────────────────────────────────────────


class GoogleAuthServiceTests(TestCase):
    """Testes para a camada de serviço de autenticação Google."""

    @patch("authentication.services.id_token.verify_oauth2_token")
    @patch(
        "authentication.services.settings.GOOGLE_CLIENT_ID",
        "test-client-id.apps.googleusercontent.com",
    )
    def test_novo_utilizador_criado_no_primeiro_login(self, mock_verify):
        """Deve criar um novo utilizador quando o google_id não existe."""
        mock_verify.return_value = make_google_payload()

        user, is_new = GoogleAuthService.authenticate_or_create_user("fake-token")

        self.assertTrue(is_new)
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.name, "Test User")
        self.assertEqual(user.google_id, "123456789")
        self.assertTrue(user.is_new_user)
        self.assertFalse(user.has_usable_password())

    @patch("authentication.services.id_token.verify_oauth2_token")
    @patch(
        "authentication.services.settings.GOOGLE_CLIENT_ID",
        "test-client-id.apps.googleusercontent.com",
    )
    def test_utilizador_existente_nao_duplicado(self, mock_verify):
        """Deve retornar o utilizador existente no segundo login."""
        mock_verify.return_value = make_google_payload()

        # Primeiro login
        user1, is_new1 = GoogleAuthService.authenticate_or_create_user("fake-token")
        # Segundo login
        user2, is_new2 = GoogleAuthService.authenticate_or_create_user("fake-token")

        self.assertTrue(is_new1)
        self.assertFalse(is_new2)
        self.assertEqual(user1.pk, user2.pk)
        self.assertEqual(User.objects.count(), 1)

    @patch("authentication.services.id_token.verify_oauth2_token")
    @patch(
        "authentication.services.settings.GOOGLE_CLIENT_ID",
        "test-client-id.apps.googleusercontent.com",
    )
    def test_conta_existente_vinculada_ao_google(self, mock_verify):
        """Deve vincular google_id a uma conta criada sem Google."""
        # Cria conta prévia sem google_id
        existing_user = User.objects.create_user(
            email="test@example.com",
            name="Existing User",
            password="some-password",
        )

        mock_verify.return_value = make_google_payload()
        user, is_new = GoogleAuthService.authenticate_or_create_user("fake-token")

        self.assertFalse(is_new)
        self.assertEqual(user.pk, existing_user.pk)
        user.refresh_from_db()
        self.assertEqual(user.google_id, "123456789")

    @patch("authentication.services.id_token.verify_oauth2_token")
    @patch(
        "authentication.services.settings.GOOGLE_CLIENT_ID",
        "test-client-id.apps.googleusercontent.com",
    )
    def test_token_invalido_levanta_excecao(self, mock_verify):
        """Deve lançar InvalidGoogleTokenException para token inválido."""
        mock_verify.side_effect = ValueError("Token invalid")

        with self.assertRaises(InvalidGoogleTokenException):
            GoogleAuthService.authenticate_or_create_user("invalid-token")

    @patch("authentication.services.id_token.verify_oauth2_token")
    @patch(
        "authentication.services.settings.GOOGLE_CLIENT_ID",
        "test-client-id.apps.googleusercontent.com",
    )
    def test_email_nao_verificado_levanta_excecao(self, mock_verify):
        """Deve rejeitar tokens de contas sem email verificado."""
        mock_verify.return_value = make_google_payload(email_verified=False)

        with self.assertRaises(InvalidGoogleTokenException):
            GoogleAuthService.authenticate_or_create_user("fake-token")


# ─── Testes dos Endpoints da API ──────────────────────────────────────────────


class GoogleLoginViewTests(APITestCase):
    """Testes de integração para o endpoint POST /api/auth/google/."""

    url = "/api/auth/google/"

    @patch("authentication.services.id_token.verify_oauth2_token")
    @patch(
        "authentication.services.settings.GOOGLE_CLIENT_ID",
        "test-client-id.apps.googleusercontent.com",
    )
    def test_novo_utilizador_retorna_201(self, mock_verify):
        """Deve retornar 201 com tokens e dados do user no primeiro login."""
        mock_verify.return_value = make_google_payload()

        response = self.client.post(
            self.url, {"id_token": "valid-token"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertTrue(data["is_new_user"])
        self.assertEqual(data["user"]["email"], "test@example.com")

    @patch("authentication.services.id_token.verify_oauth2_token")
    @patch(
        "authentication.services.settings.GOOGLE_CLIENT_ID",
        "test-client-id.apps.googleusercontent.com",
    )
    def test_utilizador_existente_retorna_200(self, mock_verify):
        """Deve retornar 200 no segundo login."""
        mock_verify.return_value = make_google_payload()

        self.client.post(self.url, {"id_token": "valid-token"}, format="json")
        response = self.client.post(
            self.url, {"id_token": "valid-token"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()["is_new_user"])

    def test_sem_id_token_retorna_400(self):
        """Deve retornar 400 se id_token não for enviado."""
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("authentication.services.id_token.verify_oauth2_token")
    @patch(
        "authentication.services.settings.GOOGLE_CLIENT_ID",
        "test-client-id.apps.googleusercontent.com",
    )
    def test_token_invalido_retorna_401(self, mock_verify):
        """Deve retornar 401 para token inválido."""
        mock_verify.side_effect = ValueError("Token invalid")

        response = self.client.post(self.url, {"id_token": "bad-token"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MeViewTests(APITestCase):
    """Testes para o endpoint GET /api/auth/me/."""

    url = "/api/auth/me/"

    def setUp(self):
        self.user = User.objects.create_user(
            email="me@example.com",
            name="Me User",
            google_id="google-123",
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def test_utilizador_autenticado_recebe_dados(self):
        """Deve retornar os dados do utilizador com token válido."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["email"], "me@example.com")

    def test_sem_token_retorna_401(self):
        """Deve retornar 401 sem Authorization header."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
