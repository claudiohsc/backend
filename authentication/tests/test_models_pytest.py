import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_user_factory_creates_valid_user(user_factory):
    user = user_factory.create()
    assert user.pk is not None
    assert "@" in user.email
    assert not user.has_usable_password()


@pytest.mark.django_db
def test_user_email_is_unique(user_factory):
    u1 = user_factory.create()
    u2 = user_factory.create()
    assert u1.email != u2.email
    assert User.objects.count() == 2
