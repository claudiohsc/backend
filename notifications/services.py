import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from .models import EmailLog
from .templates_registry import TEMPLATES_REGISTRY

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def send(template_name: str, recipient: str, context: dict) -> EmailLog:
        registry = TEMPLATES_REGISTRY.get(template_name)
        if not registry:
            raise ValueError(f"Template desconhecido: {template_name}")

        subject = registry["subject"]
        log = EmailLog.objects.create(
            recipient_email=recipient,
            template_name=template_name,
            subject=subject,
            context=context,
            status=EmailLog.Status.PENDING,
            provider=settings.EMAIL_BACKEND.split(".")[-1],
        )

        try:
            txt_body = render_to_string(registry["txt_template"], context)
            html_body = render_to_string(registry["html_template"], context)

            msg = EmailMultiAlternatives(
                subject=subject,
                body=txt_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send()

            log.status = EmailLog.Status.SENT
            log.sent_at = timezone.now()
            log.save(update_fields=["status", "sent_at"])

        except Exception as exc:
            logger.exception("Falha ao enviar e-mail [%s] para %s", template_name, recipient)
            log.status = EmailLog.Status.FAILED
            log.error_message = str(exc)
            log.save(update_fields=["status", "error_message"])

        return log
