from django.core.management.base import BaseCommand

from notifications.services import NotificationService


class Command(BaseCommand):
    help = "Envia um e-mail de teste usando NotificationService"

    def add_arguments(self, parser):
        parser.add_argument("recipient", type=str, help="E-mail destinatário")
        parser.add_argument(
            "--template",
            default="WELCOME",
            choices=[
                "ORDER_PLACED",
                "PAYMENT_CONFIRMED",
                "ORDER_SHIPPED",
                "PASSWORD_RESET",
                "WELCOME",
                "LOW_STOCK_ALERT",
            ],
            help="Template a usar (default: WELCOME)",
        )

    def handle(self, *args, **options):
        recipient = options["recipient"]
        template = options["template"]
        context = {"name": "Teste", "email": recipient}

        self.stdout.write(f"Enviando {template} para {recipient}...")
        log = NotificationService.send(template, recipient, context)
        self.stdout.write(self.style.SUCCESS(f"EmailLog #{log.id} status={log.status}"))
