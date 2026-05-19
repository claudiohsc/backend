import logging

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)


class R2MediaStorage(S3Boto3Storage):
    """Backend de storage para Cloudflare R2 (S3-compatible).

    Usado em prod para armazenar imagens de produto.
    Configuração por field: storage=R2MediaStorage() em ImageField.
    """

    default_acl = None  # R2 não usa ACLs S3-style
    file_overwrite = False  # nunca sobrescrever arquivo existente
    querystring_auth = False  # URLs públicas sem assinatura
    location = "products/"  # prefixo dentro do bucket

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("bucket_name", settings.R2_BUCKET_NAME)
        kwargs.setdefault("endpoint_url", settings.R2_ENDPOINT_URL)
        kwargs.setdefault("access_key", settings.R2_ACCESS_KEY_ID)
        kwargs.setdefault("secret_key", settings.R2_SECRET_ACCESS_KEY)
        if settings.R2_PUBLIC_BASE_URL:
            kwargs.setdefault(
                "custom_domain",
                settings.R2_PUBLIC_BASE_URL.replace("https://", ""),
            )
        super().__init__(*args, **kwargs)
