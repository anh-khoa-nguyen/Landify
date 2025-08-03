from django.utils.html import format_html
from django.urls import reverse
from twilio.rest import Client
from django.conf import settings
from datetime import datetime
import random
from django.core.cache import cache
import requests
import json
import os
from django.conf import settings

def _load_feng_shui_rules():
    file_path = os.path.join(settings.BASE_DIR, 'landifys', 'rules', 'fengshui.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"LỖI: Không thể nạp file quy tắc phong thủy: {e}")
        return {}

# --- NẠP QUY TẮC VÀO CÁC BIẾN TOÀN CỤC ---
# Đoạn code này sẽ chạy một lần duy nhất khi server Django khởi động
_RULES_DATA = _load_feng_shui_rules()
RELATIONSHIP_RULES = _RULES_DATA.get('relationship_rules', {})
FENG_SHUI_RULES = _RULES_DATA.get('feng_shui_rules', {})

def calculate_menh(birth_year: int) -> str | None:
    """
    Tính Mệnh Ngũ Hành dựa trên năm sinh.
    Phương pháp này dựa vào Thiên Can của năm sinh (tính theo Âm lịch).

    Args:
        birth_year (int): Năm sinh của người dùng.

    Returns:
        str: Tên Mệnh ("Kim", "Mộc", "Thủy", "Hỏa", "Thổ").
        None: Nếu năm sinh không hợp lệ.
    """
    if not isinstance(birth_year, int) or birth_year <= 0:
        return None

    # Ánh xạ từ số cuối của năm sinh ra Thiên Can
    # Ví dụ: 1990 -> 0 -> Canh, 1991 -> 1 -> Tân
    can_map = {
        0: 'Canh', 1: 'Tân', 2: 'Nhâm', 3: 'Quý', 4: 'Giáp',
        5: 'Ất', 6: 'Bính', 7: 'Đinh', 8: 'Mậu', 9: 'Kỷ'
    }

    # Ánh xạ từ Thiên Can ra Mệnh Ngũ Hành tương ứng
    menh_map = {
        'Giáp': 'Mộc', 'Ất': 'Mộc',
        'Bính': 'Hỏa', 'Đinh': 'Hỏa',
        'Mậu': 'Thổ', 'Kỷ': 'Thổ',
        'Canh': 'Kim', 'Tân': 'Kim',
        'Nhâm': 'Thủy', 'Quý': 'Thủy'
    }

    # Lấy chữ số cuối cùng của năm sinh
    last_digit = birth_year % 10

    # Tìm Thiên Can từ chữ số cuối
    thien_can = can_map.get(last_digit)

    # Từ Thiên Can, tìm ra Mệnh
    if thien_can:
        return menh_map.get(thien_can)

    return None

def analyze_feng_shui_rules(user_menh: str, property_direction: str, direction_element: str) -> dict:
    if not user_menh or not property_direction:
        return {"score": 0, "analysis": "Không đủ thông tin Mệnh hoặc Hướng nhà để phân tích."}

    rules = FENG_SHUI_RULES.get(user_menh)
    if not rules:
        return {"score": 0, "analysis": f"Mệnh '{user_menh}' không hợp lệ."}

    analysis = f"Gia chủ mệnh {user_menh}, nhà hướng {property_direction} (thuộc hành {direction_element}). "

    if property_direction in rules["good"]:
        score = 95
        analysis += f"Đây là mối quan hệ {RELATIONSHIP_RULES.get('good', '')}. Hướng nhà này sẽ mang lại nhiều may mắn, vượng khí và tài lộc."
    elif property_direction in rules["neutral"]:
        score = 75
        analysis += f"Đây là mối quan hệ {RELATIONSHIP_RULES.get('neutral', '')}. Hướng nhà này tốt, giúp cuộc sống ổn định, bình an."
    elif property_direction in rules["bad"]:
        score = 30
        analysis += f"Đây là mối quan hệ {RELATIONSHIP_RULES.get('bad', '')}. Hướng nhà này không hợp với tuổi của gia chủ."
    else:
        score = 50
        analysis += "Hiện chưa có đủ dữ liệu để đánh giá chi tiết về hướng này."

    return {"score": score, "analysis": analysis}