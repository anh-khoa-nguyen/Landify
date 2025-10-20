from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from apps.common.mixins import DynamicFieldsMixin
from apps.common.utils import hashids
from apps.users.serializers import UserSerializer

from .models import ModerationAction, Protest, Report

# ==============================================================================
# MODERATION SERIALIZERS
# ==============================================================================


class ReportSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """Serializer cho model Report (Báo cáo vi phạm)."""

    reporter = UserSerializer(read_only=True, fields=("id", "get_full_name"))
    reported_item_type_name = serializers.ChoiceField(choices=Report.ItemType.choices, write_only=True)
    reported_item_id = serializers.CharField(write_only=True)

    class Meta:
        model = Report
        fields = [
            "id",
            "reporter",
            "description",
            "status",
            "reported_item_type_name",
            "reported_item_id",
            "created_date",
            "updated_date",
        ]
        read_only_fields = ["reporter", "status"]

    def validate(self, data):
        type_name = data.get("reported_item_type_name")
        item_id_str = data.get("reported_item_id")
        real_id = None
        try:
            if type_name == Report.ItemType.LISTING:
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
            if not content_type.model_class().objects.filter(pk=real_id).exists():
                raise serializers.ValidationError(
                    {"reported_item_id": f"Đối tượng '{type_name}' với ID '{item_id_str}' không tồn tại."}
                )

            data["reported_item_type"] = content_type
            data["reported_item_id"] = real_id

        except ContentType.DoesNotExist:
            raise serializers.ValidationError(
                {"reported_item_type_name": f"Loại đối tượng '{type_name}' không hợp lệ."}
            )

        return data

    def create(self, validated_data):
        # Loại bỏ trường 'write_only' không thuộc về model trước khi tạo
        validated_data.pop('reported_item_type_name', None)

        # Gọi phương thức create mặc định của ModelSerializer với dữ liệu đã được làm sạch
        return super().create(validated_data)


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
