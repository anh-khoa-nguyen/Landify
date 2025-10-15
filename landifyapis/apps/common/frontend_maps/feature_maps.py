# D:\Backend\Landify\landifyapis\apps\common\frontend_maps\feature_maps.py

# ==============================================================================
# ÁNH XẠ CHO PROPERTY FEATURES
# ==============================================================================
# Key: `code` của PropertyFeature (giống hệt trong CSDL)
# Value: Một dictionary chứa các thuộc tính bổ sung cho frontend.

PROPERTY_FEATURE_MAP = {
    # === Đặc điểm kỹ thuật (TECHNICAL) ===
    "BALCONY_DIRECTION": {"icon_code": "wind"},
    "FACADE_WIDTH": {"icon_code": "rulerHorizontal", "unit": "m"},
    "ROAD_WIDTH": {"icon_code": "road", "unit": "m"},
    "NUM_FLOORS": {"icon_code": "layerGroup"},
    "NUM_BEDROOMS": {"icon_code": "bed"},
    "NUM_BATHROOMS": {"icon_code": "bath"},
    # === Nội thất (INTERIOR) ===
    "INTERIOR_STATUS": {"icon_code": "couch"},
    "HAS_AC": {"icon_code": "snowflake"},
    "HAS_HEATER": {"icon_code": "temperatureHigh"},
    # === Tiện nghi (AMENITY) ===
    "HAS_CAR_PARKING": {"icon_code": "squareParking"},
    "HAS_GARDEN": {"icon_code": "tree"},
    "HAS_POOL": {"icon_code": "waterLadder"},
    "HAS_GYM": {"icon_code": "dumbbell"},
    # === Tiện ích lân cận (NEARBY) ===
    "NEAR_SCHOOL": {"icon_code": "school"},
    "NEAR_HOSPITAL": {"icon_code": "hospital"},
    # Thêm một vài ví dụ khác cho đầy đủ
    "NEAR_SUPERMARKET": {"icon_code": "cartShopping"},
    "NEAR_PARK": {"icon_code": "treeCity"},
}

# Giá trị mặc định nếu một feature không được định nghĩa trong map
DEFAULT_FEATURE_INFO = {"icon_code": "circleInfo", "unit": None}


def get_feature_frontend_info(feature_code: str) -> dict:
    """
    Hàm tiện ích để lấy thông tin frontend cho một feature DỰA TRÊN `CODE`.
    Trả về thông tin mặc định nếu không tìm thấy.
    """
    # Lấy thông tin từ map, nếu không có thì dùng DEFAULT_FEATURE_INFO
    feature_info = PROPERTY_FEATURE_MAP.get(feature_code, DEFAULT_FEATURE_INFO)

    # Đảm bảo kết quả trả về luôn có đủ các key
    return {
        "icon_code": feature_info.get("icon_code", DEFAULT_FEATURE_INFO["icon_code"]),
        "unit": feature_info.get("unit"),  # Trả về None nếu không có unit
    }
