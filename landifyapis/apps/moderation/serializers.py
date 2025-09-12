from rest_framework import serializers

from apps.common.mixins import DynamicFieldsMixin
from apps.users.serializers import UserSerializer
from apps.common.utils import hashids

from .models import Protest, Report

# ==============================================================================
# MODERATION SERIALIZERS
# ==============================================================================

class ReportSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """Serializer cho model Report (Báo cáo vi phạm)."""

    # Hiển thị thông tin cơ bản của người báo cáo
    reporter = UserSerializer(read_only=True, fields=("id", "get_full_name"))
    reported_public_id = serializers.CharField(
        write_only=True,
        required=True,
        label="Public ID của đối tượng bị báo cáo"
    )

    class Meta:
        model = Report
        # 2. Loại bỏ `reported_item_id` khỏi danh sách `fields` để tránh bị ghi đè
        #    Chúng ta sẽ điền nó thủ công trong phương thức `create`.
        fields = [
            'id',
            'reporter',
            'description',
            'status',
            'reported_item_type',
            'reported_public_id', # Thêm trường mới vào đây
            'created_date',
            'updated_date'
        ]
        read_only_fields = ["reporter", "status"]

    def create(self, validated_data):
        # Lấy public_id mà frontend gửi lên
        public_id = validated_data.pop('reported_public_id')

        # Giải mã public_id ra ID thật
        real_id = hashids.decode_public_id(public_id)

        # Kiểm tra xem giải mã có thành công không
        if real_id is None:
            raise serializers.ValidationError({"reported_public_id": "ID không hợp lệ."})

        # "Bơm" ID thật vào `validated_data` trước khi tạo đối tượng
        validated_data['reported_item_id'] = real_id

        # Gọi hàm create gốc để tạo báo cáo như bình thường
        return super().create(validated_data)


class ProtestSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """Serializer cho model Protest (Kháng nghị)."""

    # Hiển thị thông tin của người kháng nghị và admin xử lý
    protester = UserSerializer(read_only=True, fields=("id", "get_full_name"))
    admin = UserSerializer(read_only=True, fields=("id", "get_full_name"))

    # Thêm trường ảo để hiển thị tiêu đề tin đăng cho dễ nhận biết
    listing_title = serializers.CharField(source="listing.title", read_only=True)

    class Meta:
        model = Protest
        fields = [
            "id",
            "listing",
            "listing_title",
            "protester",
            "reason",
            "admin",
            "resolution_note",
            "status",
            "created_date",
            "updated_date",
        ]
        read_only_fields = ["protester", "admin", "status", "resolution_note"]
        # Trường 'listing' sẽ được ghi vào từ view/service, nên ở đây có thể để write_only
        extra_kwargs = {"listing": {"write_only": True}}
