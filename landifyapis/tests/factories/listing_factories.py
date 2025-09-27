# tests/factories/listing_factories.py
import factory
from landifys import models
from .property_factories import PropertyFactory
from .user_factories import UserFactory

class ListingTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ListingType
    name = factory.Sequence(lambda n: f"Listing Type {n}")

class UnitPriceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.UnitPrice
    name = factory.Sequence(lambda n: f"Đơn vị {n}")
    code = factory.Sequence(lambda n: f"UNIT_{n}")

class ListingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Listing
    property = factory.SubFactory(PropertyFactory)
    user = factory.SelfAttribute('property.owner')
    listing_type = factory.SubFactory(ListingTypeFactory)
    title = factory.Sequence(lambda n: f"Bán nhà gấp lần {n}")
    content = "Nội dung chi tiết của tin đăng."

class BuySellDetailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.BuySellDetail
    listing = factory.SubFactory('landifys.tests.factories.ListingFactory')
    is_mortgaged = False

class RentalDetailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.RentalDetail
    listing = factory.SubFactory('landifys.tests.factories.ListingFactory')
    deposit_amount = factory.Faker('pydecimal', left_digits=8, right_digits=2, positive=True)
    min_lease_duration = 12

class ProjectDetailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ProjectDetail
    listing = factory.SubFactory('landifys.tests.factories.ListingFactory')
    developer = factory.Faker('company')
    total_units = factory.Faker('random_int', min=100, max=1000)