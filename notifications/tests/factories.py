import factory

from notifications.models import EmailLog


class EmailLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EmailLog

    recipient_email = factory.Sequence(lambda n: f"user{n}@example.com")
    template_name = EmailLog.Template.WELCOME
    subject = "Bem-vindo à Shio!"
    context = factory.LazyAttribute(lambda o: {"name": "Teste", "email": o.recipient_email})
    status = EmailLog.Status.PENDING
    provider = "ConsoleEmailBackend"
