import factory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Faker("name", locale="pt_BR")
    google_id = factory.Sequence(lambda n: f"google_id_{n}")
    is_new_user = True
    avatar_url = factory.Faker("image_url")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # Usa create_user para garantir senha não-utilizável (padrão OAuth)
        return model_class.objects.create_user(*args, **kwargs, password=None)
