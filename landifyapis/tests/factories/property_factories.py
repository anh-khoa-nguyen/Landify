# tests/factories/property_factories.py
import factory
from landifys import models
from .user_factories import UserFactory
from .address_factories import WardFactory

class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Location
    street = "123 Test Street"
    ward = factory.SubFactory(WardFactory)

class PropertyTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PropertyType
    name = factory.Sequence(lambda n: f"Property Type {n}")

class PropertyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Property
    owner = factory.SubFactory(UserFactory)
    location = factory.SubFactory(LocationFactory)
    property_type = factory.SubFactory(PropertyTypeFactory)
    area = 100.0

class PropertyMediaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PropertyMedia
    property = factory.SubFactory(PropertyFactory)
    url = factory.Faker('image_url')
    public_id = factory.Sequence(lambda n: f"media_public_id_{n}")