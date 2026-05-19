import pytest

from authentication.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def use_locmem_email_backend(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture
def user_factory():
    return UserFactory


@pytest.fixture
def admin_factory():
    return UserFactory  # usar admin_factory.create(is_staff=True, is_superuser=True)
