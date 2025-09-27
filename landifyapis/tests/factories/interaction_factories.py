# tests/factories/interaction_factories.py
import factory
from datetime import timedelta
from django.utils import timezone
from landifys import models
from .user_factories import UserFactory
from .property_factories import PropertyFactory
from .listing_factories import ListingFactory

class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Review
    user = factory.SubFactory(UserFactory)
    property = factory.SubFactory(PropertyFactory)
    rating = 5
    comment = factory.Faker('paragraph', nb_sentences=3)

class WishlistFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Wishlist
    user = factory.SubFactory(UserFactory)
    listing = factory.SubFactory(ListingFactory)

class AppointmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Appointment
    listing = factory.SubFactory(ListingFactory)
    user = factory.SubFactory(UserFactory)
    appointment_date = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))