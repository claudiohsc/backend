import logging

from django.db import models

logger = logging.getLogger(__name__)


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="criado em",
        help_text="Data e hora de criação do registro.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="atualizado em",
        help_text="Data e hora da última atualização do registro.",
    )

    class Meta:
        abstract = True
