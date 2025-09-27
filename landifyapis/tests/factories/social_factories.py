# tests/factories/social_factories.py
import factory
from landifys import models
from .user_factories import UserFactory

class PostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Post
    user = factory.SubFactory(UserFactory)
    title = factory.Faker('sentence', nb_words=6)
    content = factory.Faker('paragraph', nb_sentences=5)

class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Comment
    user = factory.SubFactory(UserFactory)
    post = factory.SubFactory(PostFactory)
    content = factory.Faker('sentence', nb_words=10)

class ReactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Reaction
    user = factory.SubFactory(UserFactory)
    post = factory.SubFactory(PostFactory)
    type = models.Reaction.Type.LIKE
