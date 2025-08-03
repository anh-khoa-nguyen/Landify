from rest_framework import serializers
from landifys.models import *


class UserSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['item_image'] = instance.item_image.url if hasattr(instance, 'item_image') and instance.item_image else None
        return rep

    def create(self, validated_data):
        data = validated_data.copy()
        user = User(**data)
        user.set_password(data["password"])
        user.save()
        return user

    class Meta:
        model = User
        fields = "__all__"
        extra_kwargs = {
            'password': {'write_only': True}
        }


# =================== PROPERTY & RELATED MODELS ==========================

class PropertyTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyType
        fields = "__all__"

class DirectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Direction
        fields = "__all__"

class UtilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Utility
        fields = "__all__"

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = "__all__"

class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = "__all__"

class WardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = "__all__"

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = "__all__"

class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = "__all__"

class PropertyUtilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyUtility
        fields = "__all__"

class ListingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingType
        fields = "__all__"

class ListingSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Listing
        fields = "__all__"

class PropertyMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyMedia
        fields = "__all__"

class AnalysisDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisData
        fields = "__all__"

# =================== INTERACTION ==========================

class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    property = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = "__all__"

class WishlistSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Wishlist
        fields = "__all__"

class AppointmentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Appointment
        fields = "__all__"

class ContractTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractType
        fields = "__all__"

class ContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = "__all__"

# =================== SOCIAL ==========================

class PostSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Post
        fields = "__all__"

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = "__all__"

class ReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reaction
        fields = "__all__"

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = "__all__"

# =================== NOTIFICATION & REPORT ==========================

class NotificationCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationCategory
        fields = "__all__"

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"

class ReportSerializer(serializers.ModelSerializer):
    reporter = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Report
        fields = "__all__"


class ProtestSerializer(serializers.ModelSerializer):
    # protester = serializers.HiddenField(default=serializers.CurrentUserDefault())
    protester = serializers.PrimaryKeyRelatedField(read_only=True)
    # listing sẽ được lấy từ URL, nên không cần client gửi lên
    listing = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Protest
        # Client chỉ cần gửi lên lý do kháng nghị
        fields = ['id', 'listing', 'protester', 'reason', 'status', 'created_date']
        read_only_fields = ['status', 'created_date']