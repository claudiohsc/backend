import logging

from django.db import models

from shared.models import TimestampedModel

logger = logging.getLogger(__name__)


class EmailLog(TimestampedModel):
    class Template(models.TextChoices):
        ORDER_PLACED = "ORDER_PLACED", "Pedido criado"
        PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED", "Pagamento confirmado"
        ORDER_SHIPPED = "ORDER_SHIPPED", "Pedido enviado"
        PASSWORD_RESET = "PASSWORD_RESET", "Reset de senha"
        WELCOME = "WELCOME", "Boas-vindas"
        LOW_STOCK_ALERT = "LOW_STOCK_ALERT", "Alerta de estoque baixo"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        SENT = "SENT", "Enviado"
        FAILED = "FAILED", "Falhou"
        BOUNCED = "BOUNCED", "Bounce"

    recipient_email = models.EmailField(verbose_name="e-mail destinatário")
    template_name = models.CharField(
        max_length=30,
        choices=Template.choices,
        verbose_name="template",
    )
    subject = models.CharField(max_length=255, verbose_name="assunto")
    context = models.JSONField(
        default=dict,
        verbose_name="contexto",
        help_text="Variáveis passadas ao template no momento do envio.",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="status",
    )
    provider = models.CharField(
        max_length=30,
        default="",
        verbose_name="provider",
        help_text="sendgrid | console",
    )
    provider_message_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="ID da mensagem no provider",
    )
    error_message = models.TextField(
        blank=True,
        default="",
        verbose_name="mensagem de erro",
    )
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="enviado em")

    class Meta:
        verbose_name = "log de e-mail"
        verbose_name_plural = "logs de e-mail"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient_email", "template_name"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.template_name} → {self.recipient_email} [{self.status}]"
