# tests/factories/user_factories.py
import factory
from landifys import models

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = "Test"
    last_name = factory.Sequence(lambda n: f"User{n}")

class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.UserProfile
    user = factory.SubFactory(UserFactory)