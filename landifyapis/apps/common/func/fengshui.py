import json
import os
from functools import lru_cache

from django.conf import settings

# --- NẠP QUY TẮC PHONG THỦY MỘT CÁCH HIỆU QUẢ ---

@lru_cache(maxsize=1)
def _load_feng_shui_rules():
    """
    Nạp các quy tắc từ file JSON.
    Hàm này sẽ chỉ thực sự đọc file một lần duy nhất nhờ lru_cache.
    """
    file_path = os.path.join(settings.BASE_DIR, "landifys", "rules", "fengshui.json")
    print("Đang nạp file quy tắc phong thủy...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # Trong môi trường production, bạn nên dùng logging thay vì print
        print(f"LỖI NGHIÊM TRỌNG: Không thể nạp file quy tắc phong thủy: {e}")
        # Trả về một dict rỗng để tránh làm crash ứng dụng
        return {}


def calculate_menh(birth_year: int) -> str | None:
    """
    Tính Mệnh Ngũ Hành (Niên Mệnh) dựa trên Thiên Can của năm sinh.

    Args:
        birth_year (int): Năm sinh của người dùng.

    Returns:
        str: Tên Mệnh ("Kim", "Mộc", "Thủy", "Hỏa", "Thổ") hoặc None nếu năm sinh không hợp lệ.
    """
    if not isinstance(birth_year, int) or birth_year <= 1900:
        return None

    # Lấy chữ số cuối cùng của năm sinh
    last_digit = birth_year % 10

    # Ánh xạ từ số cuối của năm sinh ra Mệnh Ngũ Hành tương ứng
    # Đây là cách viết gọn hơn, kết hợp 2 map của bạn lại
    menh_map = {
        0: "Kim",  # Canh
        1: "Kim",  # Tân
        2: "Thủy",  # Nhâm
        3: "Thủy",  # Quý
        4: "Mộc",  # Giáp
        5: "Mộc",  # Ất
        6: "Hỏa",  # Bính
        7: "Hỏa",  # Đinh
        8: "Thổ",  # Mậu
        9: "Thổ",  # Kỷ
    }

    return menh_map.get(last_digit)


def analyze_feng_shui_rules(user_menh: str, property_direction: str) -> dict:
    """
    Phân tích độ tương hợp giữa Mệnh của gia chủ và Hướng nhà.

    Args:
        user_menh (str): Mệnh của người dùng (VD: "Kim", "Mộc").
        property_direction (str): Hướng nhà (VD: "Đông", "Tây Nam").

    Returns:
        dict: Một dictionary chứa điểm số và nội dung phân tích.
    """
    rules_data = _load_feng_shui_rules()

    # Lấy các quy tắc từ dữ liệu đã nạp
    FENG_SHUI_RULES = rules_data.get("feng_shui_rules", {})
    RELATIONSHIP_RULES = rules_data.get("relationship_rules", {})
    DIRECTION_ELEMENTS = rules_data.get("direction_elements", {})

    if not all([user_menh, property_direction]):
        return {"score": 0, "analysis": "Không đủ thông tin Mệnh hoặc Hướng nhà để phân tích."}

    # Tối ưu: Tự tra cứu hành của hướng nhà từ file rules
    direction_element = DIRECTION_ELEMENTS.get(property_direction, "Không rõ")

    rules_for_menh = FENG_SHUI_RULES.get(user_menh)
    if not rules_for_menh:
        return {"score": 0, "analysis": f"Mệnh '{user_menh}' không hợp lệ hoặc không có trong quy tắc."}

    analysis_text = f"Gia chủ mệnh {user_menh}, nhà hướng {property_direction} (thuộc hành {direction_element}). "
    score = 50  # Điểm trung bình

    if property_direction in rules_for_menh.get("good", []):
        score = 95
        relationship = RELATIONSHIP_RULES.get("good", "Tương sinh")
        analysis_text += (
            f"Đây là mối quan hệ {relationship}. Hướng nhà này được cho là sẽ mang lại nhiều "
            f"may mắn, vượng khí và tài lộc cho gia chủ."
        )
    elif property_direction in rules_for_menh.get("neutral", []):
        score = 75
        relationship = RELATIONSHIP_RULES.get("neutral", "Tương hợp")
        analysis_text += (
            f"Đây là mối quan hệ {relationship}. Hướng nhà này tốt, giúp cuộc sống ổn định, "
            f"bình an và phát triển bền vững."
        )
    elif property_direction in rules_for_menh.get("bad", []):
        score = 30
        relationship = RELATIONSHIP_RULES.get("bad", "Tương khắc")
        analysis_text += (
            f"Đây là mối quan hệ {relationship}. Theo quan niệm phong thủy, hướng nhà này "
            f"có thể không hợp với tuổi của gia chủ, cần cân nhắc các biện pháp hóa giải."
        )
    else:
        analysis_text += "Hiện chưa có đủ dữ liệu để đánh giá chi tiết về sự tương hợp của hướng này."

    return {"score": score, "analysis": analysis_text}
