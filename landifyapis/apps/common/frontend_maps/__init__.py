# landifys/frontend_maps/feature_maps.py

# ==============================================================================
# ÁNH XẠ CHO PROPERTY FEATURES
# ==============================================================================
# Key: Tên của PropertyFeature (giống hệt trong CSDL)
# Value: Một dictionary chứa các thuộc tính bổ sung cho frontend.

PROPERTY_FEATURE_MAP = {
    # Đặc điểm về vị trí & hướng
    "Hướng nhà": {"icon_class": "re__icon-front-view", "display_group": "Vị trí & Hướng"},
    "Hướng ban công": {"icon_class": "re__icon-balcony", "display_group": "Vị trí & Hướng"},
    "Mặt tiền": {
        "icon_class": "re__icon-facade",
        "display_group": "Vị trí & Hướng",
        "unit": "m",  # Thêm đơn vị để frontend hiển thị
    },
    "Độ rộng đường": {"icon_class": "re__icon-road-width", "display_group": "Vị trí & Hướng", "unit": "m"},
    # Đặc điểm về cấu trúc & phòng ốc
    "Số tầng": {"icon_class": "re__icon-floors", "display_group": "Cấu trúc & Phòng ốc"},
    "Số phòng ngủ": {"icon_class": "re__icon-bedroom", "display_group": "Cấu trúc & Phòng ốc"},
    "Số phòng tắm": {"icon_class": "re__icon-bathroom", "display_group": "Cấu trúc & Phòng ốc"},
    # Đặc điểm về nội thất & tiện ích
    "Tình trạng nội thất": {"icon_class": "re__icon-furniture", "display_group": "Nội thất & Tiện ích"},
    "Có chỗ đỗ ô tô": {"icon_class": "re__icon-car-parking", "display_group": "Nội thất & Tiện ích"},
}

# Giá trị mặc định nếu một feature không được định nghĩa trong map
DEFAULT_FEATURE_INFO = {"icon_class": "re__icon-default-feature", "display_group": "Thông tin khác"}


def get_feature_frontend_info(feature_name: str) -> dict:
    """
    Hàm tiện ích để lấy thông tin frontend cho một feature.
    Trả về thông tin mặc định nếu không tìm thấy.
    """
    return PROPERTY_FEATURE_MAP.get(feature_name, DEFAULT_FEATURE_INFO)
