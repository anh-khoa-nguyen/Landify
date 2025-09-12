# landifys/serializers/interactions.py

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from apps.common.mixins import DynamicFieldsMixin
from apps.common.utils.hashids import decode_public_id
from apps.listings.models import Listing

from .models import Appointment, Review, Wishlist, Chat, Cooperation, Message

from apps.users.serializers import UserSerializer

from apps.listings.models import Property
from apps.listings.serializers import ListingDetailSerializer, ListingPreviewSerializer


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
        # Đổi tên key từ 'listing_public_id' thành 'listing' để khớp với model
        validated_data['listing'] = validated_data.pop('listing_public_id')
        return super().create(validated_data)

class ReviewSerializer(serializers.ModelSerializer):
    # user và property sẽ là chỉ đọc trong response
    user = UserSerializer(read_only=True, fields=("id", "get_full_name", "profile.avatar"))
    property = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Review
        # Chỉ bao gồm các trường mà client gửi lên và các trường read_only
        fields = [
            'id',
            'user',
            'property',
            'rating',
            'comment',
            'created_date',
        ]
        # Các trường này sẽ được cung cấp từ view/service, không phải từ client
        read_only_fields = ['user', 'property']

        # === XÓA BỎ VALIDATOR Ở ĐÂY ===
        # validators = [
        #     UniqueTogetherValidator(...)
        # ]

    # === THÊM PHƯƠNG THỨC VALIDATE TÙY CHỈNH ===
    def validate(self, data):
        """
        Kiểm tra xem người dùng đã đánh giá bất động sản này chưa.
        """
        # Lấy user và property từ context mà ViewSet sẽ truyền vào
        user = self.context['request'].user
        prop = self.context['property']

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
        read_only_fields = ["user"]

    def create(self, validated_data):
        # Lấy public_id và user từ validated_data
        public_id = validated_data.pop('listing_public_id')
        user = self.context['request'].user

        # Dịch public_id thành ID thật
        listing_id = decode_public_id(public_id)

        if listing_id is None:
            raise serializers.ValidationError({"listing_public_id": "ID tin đăng không hợp lệ."})

        # Kiểm tra xem người dùng đã lưu tin này chưa để tránh lỗi DB
        if Wishlist.objects.filter(user=user, listing_id=listing_id).exists():
            raise serializers.ValidationError({"detail": "Bạn đã lưu tin đăng này rồi."})

        # Tạo đối tượng Wishlist mới
        try:
            wishlist = Wishlist.objects.create(user=user, listing_id=listing_id)
            return wishlist
        except Exception as e:
            # Bắt các lỗi khác có thể xảy ra
            raise serializers.ValidationError({"detail": f"Không thể lưu tin đăng: {e}"})

#========================================================

class ChatParticipantSerializer(UserSerializer):
    """Serializer con để chỉ hiển thị thông tin cần thiết của người tham gia."""
    class Meta(UserSerializer.Meta):
        fields = ['id', 'get_full_name', 'profile'] # Giả sử UserSerializer có lồng profile

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
            'id',
            'chat_type',
            'name',
            'listing',
            'participants',  # <-- ĐẢM BẢO TRƯỜNG NÀY CÓ TRONG DANH SÁCH
            'created_date',
        ]

#========================================================
class CooperationSerializer(serializers.ModelSerializer):
    """
    Serializer cho model Hợp tác môi giới (Cooperation).
    """
    # Lồng các thông tin cần thiết để hiển thị trên UI
    listing = ListingPreviewSerializer(read_only=True)
    agent = UserSerializer(read_only=True, fields=['id', 'get_full_name', 'profile'])
    owner = UserSerializer(read_only=True, fields=['id', 'get_full_name', 'profile'])

    # Trường chỉ ghi (write-only) để nhận ID của tin đăng khi tạo yêu cầu
    listing_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Cooperation
        fields = [
            'id',
            'listing',
            'listing_id', # Dùng để tạo
            'agent',
            'owner',
            'status',
            'rejection_reason',
            'cancellation_reason',
            'created_date',
        ]
        # Các trường này sẽ được điền tự động bởi logic ở service/view
        read_only_fields = [
            'agent',
            'owner',
            'status',
            'rejection_reason',
            'cancellation_reason'
        ]
#=============================================================
class LinkedAppointmentSerializer(serializers.ModelSerializer):
    """Serializer chỉ hiển thị thông tin cần thiết của Appointment cho thẻ chat."""
    listing = ListingPreviewSerializer(read_only=True)
    class Meta:
        model = Appointment
        fields = ['id', 'appointment_date', 'status', 'listing']

    def get_listing(self, obj: Appointment):
        # Lấy context từ serializer cha (LinkedAppointmentSerializer)
        context = self.context
        # Khởi tạo ListingPreviewSerializer và truyền context xuống
        return ListingPreviewSerializer(obj.listing, context=context).data


class LinkedCooperationSerializer(serializers.ModelSerializer):
    """Serializer chỉ hiển thị thông tin cần thiết của Cooperation cho thẻ chat."""
    listing = ListingPreviewSerializer(read_only=True)
    agent = UserSerializer(read_only=True)

    class Meta:
        model = Cooperation
        fields = ['id', 'status', 'agent', 'listing']

    def get_listing(self, obj: Cooperation):
        context = self.context
        return ListingPreviewSerializer(obj.listing, context=context).data

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    linked_object_data = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id',
            'sender_id',
            'sender_name',
            'content',
            'created_date',
            'message_type',
            'attachment_url',
            # Thêm trường mới vào đây
            'linked_object_data',
        ]
        read_only_fields = ['read_by']

    def get_linked_object_data(self, obj: Message):
        if hasattr(obj, 'linked_object') and obj.linked_object:
            # Lấy context từ serializer cha (MessageSerializer)
            context = self.context

            if isinstance(obj.linked_object, Appointment):
                return {
                    "type": "appointment",
                    "data": LinkedAppointmentSerializer(obj.linked_object, context=context).data
                }
            if isinstance(obj.linked_object, Cooperation):
                return {
                    "type": "cooperation",
                    "data": LinkedCooperationSerializer(obj.linked_object, context=context).data
                }
        return None
