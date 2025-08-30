from rest_framework import serializers


# Không import models nữa vì không còn dùng Django ORM
# from landifys.models import *

# =============================================================================
# LƯU Ý QUAN TRỌNG:
# Khi chuyển sang Firestore, các Serializer này không còn kế thừa từ ModelSerializer.
# Chúng kế thừa từ serializers.Serializer và vai trò chính là VALIDATE dữ liệu
# đầu vào từ client. Logic tạo và cập nhật bản ghi trong database (Firestore)
# sẽ được xử lý hoàn toàn trong views.py sau khi serializer.is_valid() trả về True.
# =============================================================================


class UserSerializer(serializers.Serializer):
    """
    Dùng để validate dữ liệu khi tạo hoặc cập nhật hồ sơ người dùng.
    Cũng có thể dùng để định dạng dữ liệu trả về.
    """
    # Các trường client có thể gửi lên để cập nhật
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False)

    uid = serializers.CharField(read_only=True)
    phone_number = serializers.CharField(read_only=True)
    avatar = serializers.URLField(read_only=True)
    is_active = serializers.BooleanField(read_only=True, default=True)

    is_phone_verified = serializers.BooleanField(read_only=True)
    is_id_card_verified = serializers.BooleanField(read_only=True)
    is_identity_verified = serializers.BooleanField(read_only=True) # Trường mới

    role = serializers.CharField(read_only=True, default='user')
    created_at = serializers.DateTimeField(read_only=True)

    address = serializers.CharField(max_length=150, required=False)

    full_name = serializers.SerializerMethodField(read_only=True)

    def get_full_name(self, obj):
        # `obj` ở đây là một dictionary được lấy từ Firestore
        first = obj.get('first_name', '')
        last = obj.get('last_name', '')
        return f"{first} {last}".strip()


# =================== PROPERTY & RELATED MODELS ==========================
# Các serializer này chủ yếu dùng để validate cấu trúc dữ liệu lồng nhau (nested)

class LocationSerializer(serializers.Serializer):
    street = serializers.CharField(max_length=255)
    ward = serializers.CharField(max_length=100)  # Giả sử lưu tên
    district = serializers.CharField(max_length=100)
    city = serializers.CharField(max_length=100)
    lat = serializers.FloatField(required=False, allow_null=True)
    lng = serializers.FloatField(required=False, allow_null=True)


class PropertySerializer(serializers.Serializer):
    """
    Validate dữ liệu khi tạo một Bất động sản mới.
    """
    area = serializers.FloatField()
    has_legal_docs = serializers.BooleanField(default=False)
    floor_num = serializers.IntegerField(required=False, allow_null=True)
    bedroom_count = serializers.IntegerField(default=0)
    bathroom_count = serializers.IntegerField(default=0)

    # Dữ liệu lồng nhau
    location = LocationSerializer()

    # Dùng write_only để nhận ID từ client, view sẽ xử lý logic
    property_type_id = serializers.CharField(write_only=True)  # Firestore ID là string
    direction_id = serializers.CharField(write_only=True, required=False, allow_null=True)
    utility_ids = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )


class ListingSerializer(serializers.Serializer):
    """
    Validate dữ liệu khi tạo một Tin đăng mới.
    """
    title = serializers.CharField(max_length=255)
    content = serializers.CharField()
    price = serializers.DecimalField(max_digits=20, decimal_places=2)
    commission_percentage = serializers.FloatField(required=False, allow_null=True)

    # ID của property liên quan
    property_id = serializers.CharField()
    listing_type_id = serializers.CharField()


class PropertyMediaSerializer(serializers.Serializer):
    """
    Dùng để biểu diễn dữ liệu media, không dùng để tạo mới qua API
    (vì file được xử lý trực tiếp trong view).
    """
    url = serializers.URLField(read_only=True)
    media_type = serializers.CharField(read_only=True, help_text="e.g., 'image', 'video'")
    created_at = serializers.DateTimeField(read_only=True)


# =================== INTERACTION ==========================

class ReviewSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(allow_blank=True)
    # property_id sẽ được lấy từ URL, user_id lấy từ token (trong view)


class WishlistSerializer(serializers.Serializer):
    # Dùng để validate việc tạo wishlist item
    listing_id = serializers.CharField()
    # user_id sẽ được lấy từ token trong view


class AppointmentSerializer(serializers.Serializer):
    listing_id = serializers.CharField()
    appointment_date = serializers.DateTimeField()
    note = serializers.CharField(required=False, allow_blank=True)
    # user_id sẽ được lấy từ token trong view


class ListingBrokerSerializer(serializers.Serializer):
    """
    Dùng để biểu diễn thông tin một đơn xin làm môi giới.
    Dữ liệu tạo mới được xử lý trong view.
    """
    id = serializers.CharField(read_only=True)
    listing = ListingSerializer(read_only=True)  # Hiển thị thông tin tin đăng
    broker = UserSerializer(read_only=True)  # Hiển thị thông tin người môi giới
    status = serializers.CharField(read_only=True)
    created_date = serializers.DateTimeField(read_only=True)


# =================== SOCIAL ==========================

class CommentSerializer(serializers.Serializer):
    content = serializers.CharField()
    # post_id lấy từ URL, user_id lấy từ token

    # Các trường chỉ đọc để hiển thị
    user = UserSerializer(read_only=True)  # Hiển thị thông tin người comment
    created_at = serializers.DateTimeField(read_only=True)


class ReactionSerializer(serializers.Serializer):
    # Dùng để validate loại reaction
    REACTION_CHOICES = ('like', 'love', 'haha', 'wow', 'sad', 'angry')
    type = serializers.ChoiceField(choices=REACTION_CHOICES)
    # post_id lấy từ URL, user_id lấy từ token


class PostSerializer(serializers.Serializer):
    """
    Dùng để validate khi tạo và biểu diễn khi đọc một bài Post.
    """
    title = serializers.CharField(max_length=255)
    content = serializers.CharField()

    # Các trường chỉ đọc, dùng cho output
    user = UserSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True, default=[])
    reactions = ReactionSerializer(many=True, read_only=True, default=[])
    created_at = serializers.DateTimeField(read_only=True)

    # Giữ lại các method field này rất hữu ích
    comment_count = serializers.SerializerMethodField()
    reaction_count = serializers.SerializerMethodField()

    def get_comment_count(self, obj):
        # obj là dict, 'comments' là một list các dict
        if 'comments' in obj and isinstance(obj['comments'], list):
            return len(obj['comments'])
        return 0

    def get_reaction_count(self, obj):
        if 'reactions' in obj and isinstance(obj['reactions'], list):
            return len(obj['reactions'])
        return 0


class SubscriptionSerializer(serializers.Serializer):
    """
    Dùng để biểu diễn một quan hệ theo dõi. Logic tạo/xóa nằm trong view.
    """
    follower_id = serializers.CharField(read_only=True)
    following_id = serializers.CharField(read_only=True)
    followed_at = serializers.DateTimeField(read_only=True)


# =================== NOTIFICATION & REPORT ==========================

class NotificationSerializer(serializers.Serializer):
    """
    Dùng để biểu diễn thông báo. Logic tạo nằm trong hệ thống (ví dụ: Celery tasks).
    """
    id = serializers.CharField(read_only=True)
    user_id = serializers.CharField(read_only=True)
    category = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    content = serializers.CharField(read_only=True)
    is_read = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class ReportSerializer(serializers.Serializer):
    """
    Validate dữ liệu khi người dùng tạo một báo cáo.
    """
    REPORT_TYPES = ('spam', 'scam', 'inappropriate', 'other')

    report_type = serializers.ChoiceField(choices=REPORT_TYPES)
    description = serializers.CharField()

    # ID của đối tượng bị báo cáo (ví dụ: listing_id, user_id, post_id)
    # Sử dụng một trường chung để linh hoạt
    reported_item_id = serializers.CharField()
    reported_item_type = serializers.ChoiceField(choices=('listing', 'user', 'post', 'comment'))


class ProtestSerializer(serializers.Serializer):
    """
    Validate lý do khi người dùng kháng nghị.
    """
    reason = serializers.CharField()
    # listing_id sẽ lấy từ URL, protester_id sẽ lấy từ token (trong view)