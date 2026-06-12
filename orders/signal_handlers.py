from django.dispatch import receiver

from authentication.signals import google_login_completed

from .services import merge_session_cart_to_db


@receiver(google_login_completed)
def on_google_login(sender, request, user, **kwargs):
    try:
        merge_session_cart_to_db(request, user)
    except Exception:
        import logging

        logger = logging.getLogger(__name__)
        logger.exception("Erro ao mesclar carrinho da sessão após login")
