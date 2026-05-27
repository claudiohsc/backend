import tempfile

from .base import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Isolar uploads de teste do mediafiles/ real
MEDIA_ROOT = tempfile.mkdtemp(prefix="test-media-")
