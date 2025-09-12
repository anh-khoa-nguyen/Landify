# tests/factories/moderation_factories.py
import factory
from landifys import models


class ReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Report

    reporter = factory.SubFactory('landifys.tests.factories.user_factories.UserFactory')
    description = factory.Faker('paragraph', nb_sentences=2)
    reported_item_type = models.Report.ItemType.LISTING
    reported_item_id = factory.Sequence(lambda n: n + 1)


class ProtestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Protest

    listing = factory.SubFactory('landifys.tests.factories.ListingFactory')
    protester = factory.SubFactory('landifys.tests.factories.user_factories.UserFactory')
    reason = "Lý do kháng nghị mặc định."