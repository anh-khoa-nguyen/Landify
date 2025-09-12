# tests/factories/address_factories.py
import factory
from vi_address import models

class CityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.City
    name = factory.Sequence(lambda n: f"City {n}")
    slug = factory.Sequence(lambda n: f"city-{n}")
    code = factory.Sequence(lambda n: n + 1)
    type = "thanh-pho"
    name_with_type = factory.LazyAttribute(lambda obj: f"{obj.type.capitalize()} {obj.name}")

class DistrictFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.District
    parent_code = factory.SubFactory(CityFactory)
    name = factory.Sequence(lambda n: f"District {n}")
    code = factory.Sequence(lambda n: n + 100)
    type = "quan"
    name_with_type = factory.LazyAttribute(lambda obj: f"{obj.type.capitalize()} {obj.name}")
    path_with_type = factory.LazyAttribute(lambda obj: f"{obj.name_with_type}, {obj.parent_code.name_with_type}")

class WardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Ward
    parent_code = factory.SubFactory(DistrictFactory)
    name = factory.Sequence(lambda n: f"Ward {n}")
    code = factory.Sequence(lambda n: n + 10000)
    type = "phuong"
    name_with_type = factory.LazyAttribute(lambda obj: f"{obj.type.capitalize()} {obj.name}")
    path_with_type = factory.LazyAttribute(lambda obj: f"{obj.name_with_type}, {obj.parent_code.path_with_type}")