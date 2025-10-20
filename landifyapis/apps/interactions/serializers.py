# landifys/serializers/interactions.py

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from apps.common.mixins import DynamicFieldsMixin
from apps.common.utils.hashids import decode_public_id
from apps.listings.models import Listing, Property
from apps.listings.serializers import ListingDetailSerializer, ListingPreviewSerializer
from apps.users.serializers import UserSerializer

from .models import Appointment, Chat, Cooperation, Message, Review, Wishlist

# ==============================================================================
# SERIALIZER CHO CÁC TƯƠNG TÁC CHÍNH
# ==============================================================================
# Các serializer này quản lý các hành động tương tác cốt lõi của người dùng
# với tin đăng và bất động sản.


class AppointmentSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    user = UserSerializer(read_only=True, fields=("id", "get_full_name"))
    listing = ListingPreviewSerializer(read_only=True)

    listing_public_id = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "user",
            "listing",  # Chỉ cần một trường này
            "listing_public_id",
            "appointment_date",
            "note",
            "status",
            "created_date",
            "updated_date",
            "active",
        ]
        read_only_fields = ["user", "status", "listing"]

    def validate_listing_public_id(self, value):
        """
        Validate và chuyển đổi public_id thành Listing object.
        """
        listing_id = decode_public_id(value)
        if listing_id is None:
            raise serializers.ValidationError("ID tin đăng không hợp lệ.")

        try:
            listing = Listing.objects.get(pk=listing_id)
            # Kiểm tra xem người dùng có đang tự đặt lịch cho tin của mình không
            # (Tùy chọn, nhưng là một ý hay)
            # user = self.context['request'].user
            # if listing.user == user:
            #     raise serializers.ValidationError("Bạn không thể tự đặt lịch cho tin đăng của mình.")
            return listing
        except Listing.DoesNotExist:
            raise serializers.ValidationError("Tin đăng không tồn tại.")

    def create(self, validated_data):
        validated_data["listing"] = validated_data.pop("listing_public_id")
        return super().create(validated_data)


class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True, fields=("id", "get_full_name", "profile.avatar"))
    property = serializers.PrimaryKeyRelatedField(read_only=True)

    latitude = serializers.FloatField(write_only=True, required=True)
    longitude = serializers.FloatField(write_only=True, required=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "user",
            "property",
            "rating",
            "comment",
            "created_date",
            "latitude",
            "longitude",
        ]
        read_only_fields = ["user", "property"]

    def validate(self, data):
        user = self.context["request"].user
        prop = self.context["property"]

        if Review.objects.filter(user=user, property=prop).exists():
            raise serializers.ValidationError("Bạn đã đánh giá bất động sản này rồi.")

        return data


class WishlistSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    user = UserSerializer(read_only=True, fields=("id", "get_full_name"))
    listing = ListingPreviewSerializer(read_only=True)
    listing_public_id = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Wishlist
        fields = ["id", "user", "listing", "listing_public_id"]
        read_only_fields = ["user", "listing"]


# ==============================================================================
# SERIALIZER CHO NGHIỆP VỤ HỢP TÁC
# ==============================================================================
# Serializer này dành riêng cho luồng nghiệp vụ hợp tác môi giới.


class CooperationSerializer(serializers.ModelSerializer):
    """
    Serializer cho model Hợp tác môi giới (Cooperation).
    """

    listing = ListingPreviewSerializer(read_only=True)
    agent = UserSerializer(read_only=True, fields=["id", "get_full_name", "profile"])
    owner = UserSerializer(read_only=True, fields=["id", "get_full_name", "profile"])

    listing_public_id = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Cooperation
        fields = [
            "id",
            "listing",
            "listing_public_id",
            "agent",
            "owner",
            "status",
            "rejection_reason",
            "cancellation_reason",
            "created_date",
        ]
        read_only_fields = ["agent", "owner", "status", "rejection_reason", "cancellation_reason"]

    def validate_listing_public_id(self, value):
        """
        Kiểm tra xem public_id có hợp lệ và tin đăng có tồn tại không.
        """
        listing_id = decode_public_id(value)
        if listing_id is None:
            raise serializers.ValidationError("ID tin đăng không hợp lệ.")

        try:
            # Trả về đối tượng Listing để có thể sử dụng ở bước sau
            listing = Listing.objects.select_related("user").get(pk=listing_id)
            return listing
        except Listing.DoesNotExist:
            raise serializers.ValidationError("Tin đăng không tồn tại.")


# ==============================================================================
# SERIALIZER CHO HỆ THỐNG TRÒ CHUYỆN (CHAT)
# ==============================================================================
# Bao gồm các serializer để hiển thị chi tiết cuộc trò chuyện, tin nhắn,
# và các thành phần lồng nhau (thẻ tương tác).


class LinkedAppointmentSerializer(serializers.ModelSerializer):
    """Serializer chỉ hiển thị thông tin cần thiết của Appointment cho thẻ chat."""

    listing = ListingPreviewSerializer(read_only=True)

    class Meta:
        model = Appointment
        fields = ["id", "appointment_date", "status", "listing"]

    def get_listing(self, obj: Appointment):
        context = self.context
        return ListingPreviewSerializer(obj.listing, context=context).data


class LinkedCooperationSerializer(serializers.ModelSerializer):
    listing = ListingPreviewSerializer(read_only=True)
    agent = UserSerializer(read_only=True)

    class Meta:
        model = Cooperation
        fields = ["id", "status", "agent", "listing"]

    def get_listing(self, obj: Cooperation):
        context = self.context
        return ListingPreviewSerializer(obj.listing, context=context).data


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)
    sender_id = serializers.IntegerField(source="sender.id", read_only=True)
    linked_object_data = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "sender_id",
            "sender_name",
            "content",
            "created_date",
            "message_type",
            "attachment_url",
            # Thêm trường mới vào đây
            "linked_object_data",
        ]
        read_only_fields = ["read_by"]

    def get_linked_object_data(self, obj: Message):
        if hasattr(obj, "linked_object") and obj.linked_object:
            # Lấy context từ serializer cha (MessageSerializer)
            context = self.context

            if isinstance(obj.linked_object, Appointment):
                return {
                    "type": "appointment",
                    "data": LinkedAppointmentSerializer(obj.linked_object, context=context).data,
                }
            if isinstance(obj.linked_object, Cooperation):
                return {
                    "type": "cooperation",
                    "data": LinkedCooperationSerializer(obj.linked_object, context=context).data,
                }
        return None


class ChatDetailSerializer(serializers.ModelSerializer):
    """
    Serializer để hiển thị thông tin chi tiết của một cuộc trò chuyện.
    """

    # Lấy thông tin chi tiết của những người tham gia
    participants = UserSerializer(many=True, read_only=True)

    # Lấy thông tin xem trước của tin đăng liên quan (nếu có)
    listing = ListingPreviewSerializer(read_only=True)

    class Meta:
        model = Chat
        fields = [
            "id",
            "chat_type",
            "name",
            "listing",
            "participants",
            "created_date",
        ]


class ChatParticipantSerializer(UserSerializer):
    """Serializer con để chỉ hiển thị thông tin cần thiết của người tham gia."""

    class Meta(UserSerializer.Meta):
        fields = ["id", "get_full_name", "profile"]
