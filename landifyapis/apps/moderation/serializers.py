from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType

from apps.common.mixins import DynamicFieldsMixin
from apps.users.serializers import UserSerializer
from apps.common.utils import hashids

from .models import Protest, Report, ModerationAction

# ==============================================================================
# MODERATION SERIALIZERS
# ==============================================================================

class ReportSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """Serializer cho model Report (Báo cáo vi phạm)."""

    reporter = UserSerializer(read_only=True, fields=("id", "get_full_name"))
    reported_item_type_name = serializers.ChoiceField(
        choices=Report.ItemType.choices, write_only=True
    )
    reported_item_id = serializers.CharField(write_only=True)

    class Meta:
        model = Report
        fields = [
            'id',
            'reporter',
            'description',
            'status',
            'reported_item_type_name',
            'reported_item_id',
            'created_date',
            'updated_date'
        ]
        read_only_fields = ["reporter", "status"]

    def validate(self, data):
        type_name = data.get('reported_item_type_name')
        item_id_str = data.get('reported_item_id')
        real_id = None
        try:
            if type_name == Report.ItemType.LISTING:
                # Nếu là tin đăng, giải mã public_id
                real_id = hashids.decode_public_id(item_id_str)
                if real_id is None:
                    raise serializers.ValidationError({"reported_item_id": "ID của tin đăng không hợp lệ."})
            else:
                # Nếu là user, post, comment, chuyển đổi sang số nguyên
                try:
                    real_id = int(item_id_str)
                except (ValueError, TypeError):
                    raise serializers.ValidationError({"reported_item_id": "ID phải là một số nguyên."})

            # Chuyển đổi tên model (vd: "listing") thành đối tượng ContentType
            content_type = ContentType.objects.get(model=type_name)
            # Kiểm tra xem đối tượng có thực sự tồn tại không
            if not content_type.model_class().objects.filter(pk=real_id).exists():
                raise serializers.ValidationError(
                    {"reported_item_id": f"Đối tượng '{type_name}' với ID '{item_id_str}' không tồn tại."}
                )
            # "Bơm" đối tượng ContentType vào data để lưu
            data['reported_item_type'] = content_type
            data['reported_item_id'] = real_id

        except ContentType.DoesNotExist:
            raise serializers.ValidationError(
                {"reported_item_type_name": f"Loại đối tượng '{type_name}' không hợp lệ."}
            )

        return data

class ModerationActionSerializer(serializers.ModelSerializer):
    moderator = UserSerializer(read_only=True, fields=("id", "get_full_name"))

    class Meta:
        model = ModerationAction
        fields = '__all__'

class ProtestSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """Serializer cho model Protest (Kháng nghị)."""

    # Hiển thị thông tin của người kháng nghị và admin xử lý
    protester = UserSerializer(read_only=True, fields=("id", "get_full_name"))
    admin_reviewer = UserSerializer(read_only=True, fields=("id", "get_full_name"))

    action_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Protest
        fields = [
            "id",
            "action",
            "action_id",
            "protester",
            "reason",
            "admin_reviewer",
            "resolution_note",
            "status",
            "created_date",
        ]
        read_only_fields = ["protester", "admin_reviewer", "status", "resolution_note", "action"]
        # Trường 'listing' sẽ được ghi vào từ view/service, nên ở đây có thể để write_only