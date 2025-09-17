# D:\Backend\Landify\landifyapis\apps\common\frontend_maps\choices_maps.py

# === IMPORT CONSTANTS MÀ BẠN VỪA TẠO ===
from apps.listings import constants

# ==============================================================================
# ÁNH XẠ LỰA CHỌN (CHOICES) CHO CÁC PROPERTY FEATURES
# ==============================================================================

FEATURE_CHOICES_MAP = {
    "CONDITION_STATUS": [
        {"value": constants.ConditionStatus.NEW, "display_name": "Mới 100%"},
        {"value": constants.ConditionStatus.RENOVATED, "display_name": "Đã cải tạo"},
        {"value": constants.ConditionStatus.GOOD, "display_name": "Tình trạng tốt"},
        {"value": constants.ConditionStatus.NEEDS_REPAIR, "display_name": "Cần sửa chữa"}
    ],

    "INTERIOR_STATUS": [
        {"value": constants.InteriorStatus.FULL, "display_name": "Nội thất đầy đủ"},
        {"value": constants.InteriorStatus.BASIC, "display_name": "Nội thất cơ bản"},
        {"value": constants.InteriorStatus.NONE, "display_name": "Không có nội thất"}
    ],
}


def get_feature_choices(feature_code: str) -> list | None:
    """
    Hàm tiện ích để lấy danh sách các lựa chọn cho một feature DỰA TRÊN `CODE`.
    """
    return FEATURE_CHOICES_MAP.get(feature_code)