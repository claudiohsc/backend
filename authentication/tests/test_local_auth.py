import pytest
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient

from authentication.models import User
from authentication.services import InvalidCredentialsException, LocalAuthService
from notifications.models import EmailLog


@pytest.fixture
def api_client():
    return APIClient()


# ─── Service: register_user ──────────────────────────────────────────────────


@pytest.mark.django_db
def test_register_user_creates_user_with_usable_password():
    user = LocalAuthService.register_user(
        email="alice@example.com", password="SenhaSegura123", name="Alice"
    )
    assert user.email == "alice@example.com"
    assert user.name == "Alice"
    assert user.is_new_user is True
    assert user.has_usable_password()
    assert user.check_password("SenhaSegura123")


@pytest.mark.django_db
def test_register_user_normalizes_email():
    user = LocalAuthService.register_user(
        email="  Alice@Example.COM  ", password="SenhaSegura123", name="Alice"
    )
    assert user.email == "alice@example.com"


@pytest.mark.django_db
def test_register_user_sends_welcome_email():
    LocalAuthService.register_user(
        email="alice@example.com", password="SenhaSegura123", name="Alice"
    )
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["alice@example.com"]
    assert "Bem-vindo" in mail.outbox[0].subject
    assert EmailLog.objects.filter(
        recipient_email="alice@example.com",
        template_name=EmailLog.Template.WELCOME,
        status=EmailLog.Status.SENT,
    ).exists()


# ─── Service: authenticate_user ──────────────────────────────────────────────


@pytest.mark.django_db
def test_authenticate_user_success_clears_is_new_user():
    LocalAuthService.register_user(
        email="alice@example.com", password="SenhaSegura123", name="Alice"
    )
    user = LocalAuthService.authenticate_user("alice@example.com", "SenhaSegura123")
    assert user.is_new_user is False


@pytest.mark.django_db
def test_authenticate_user_wrong_password_raises():
    LocalAuthService.register_user(
        email="alice@example.com", password="SenhaSegura123", name="Alice"
    )
    with pytest.raises(InvalidCredentialsException):
        LocalAuthService.authenticate_user("alice@example.com", "senha-errada")


@pytest.mark.django_db
def test_authenticate_user_unknown_email_raises():
    with pytest.raises(InvalidCredentialsException):
        LocalAuthService.authenticate_user("ninguem@example.com", "qualquer")


@pytest.mark.django_db
def test_authenticate_user_google_only_account_raises():
    """Conta criada via Google (sem senha) não pode logar via email/senha."""
    User.objects.create_user(
        email="google@example.com",
        name="Google User",
        google_id="123",
        password=None,
    )
    with pytest.raises(InvalidCredentialsException):
        LocalAuthService.authenticate_user("google@example.com", "qualquer")


# ─── View: POST /api/auth/register/ ──────────────────────────────────────────


@pytest.mark.django_db
def test_register_endpoint_returns_201_with_tokens(api_client):
    url = reverse("authentication:register")
    resp = api_client.post(
        url,
        {
            "email": "alice@example.com",
            "password": "SenhaSegura123",
            "name": "Alice",
        },
        format="json",
    )
    assert resp.status_code == 201
    assert "access" in resp.data
    assert "refresh" in resp.data
    assert resp.data["is_new_user"] is True
    assert resp.data["user"]["email"] == "alice@example.com"


@pytest.mark.django_db
def test_register_endpoint_rejects_duplicate_email(api_client):
    User.objects.create_user(email="alice@example.com", password="x", name="Alice")
    url = reverse("authentication:register")
    resp = api_client.post(
        url,
        {"email": "alice@example.com", "password": "OutraSenha123", "name": "Outra"},
        format="json",
    )
    assert resp.status_code == 400
    assert "email" in resp.data["details"]


@pytest.mark.django_db
def test_register_endpoint_rejects_weak_password(api_client):
    url = reverse("authentication:register")
    resp = api_client.post(
        url,
        {"email": "alice@example.com", "password": "12345678", "name": "Alice"},
        format="json",
    )
    assert resp.status_code == 400
    assert "password" in resp.data["details"]


# ─── View: POST /api/auth/login/ ─────────────────────────────────────────────


@pytest.mark.django_db
def test_login_endpoint_returns_200_with_tokens(api_client):
    LocalAuthService.register_user(
        email="alice@example.com", password="SenhaSegura123", name="Alice"
    )
    url = reverse("authentication:login")
    resp = api_client.post(
        url,
        {"email": "alice@example.com", "password": "SenhaSegura123"},
        format="json",
    )
    assert resp.status_code == 200
    assert "access" in resp.data
    assert resp.data["is_new_user"] is False


@pytest.mark.django_db
def test_login_endpoint_wrong_password_returns_401(api_client):
    LocalAuthService.register_user(
        email="alice@example.com", password="SenhaSegura123", name="Alice"
    )
    url = reverse("authentication:login")
    resp = api_client.post(
        url,
        {"email": "alice@example.com", "password": "errada"},
        format="json",
    )
    assert resp.status_code == 401


@pytest.mark.django_db
def test_login_endpoint_unknown_email_returns_401(api_client):
    url = reverse("authentication:login")
    resp = api_client.post(
        url,
        {"email": "ninguem@example.com", "password": "qualquer"},
        format="json",
    )
    assert resp.status_code == 401
