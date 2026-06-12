from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "orders"

    def ready(self):
        try:
            from . import signal_handlers  # noqa: F401
        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                "Erro ao registar signal handlers do orders"
            )
