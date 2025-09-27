import pytest
from unittest.mock import patch
from landifys.func import fengshui

# ==============================================================================
# TEST CHO HÀM: calculate_menh
# ==============================================================================

# Sử dụng pytest.mark.parametrize để chạy cùng một test với nhiều bộ dữ liệu khác nhau
# Cú pháp: ("tên_tham_số", [giá_trị_1, giá_trị_2, ...])
@pytest.mark.parametrize("birth_year, expected_menh", [
    (1990, "Thổ"),  # Canh Ngọ -> Số cuối 0 -> Kim (Lỗi trong logic cũ, đúng phải là Thổ)
    (1991, "Mộc"),  # Tân Mùi -> Số cuối 1 -> Kim (Lỗi trong logic cũ, đúng phải là Mộc)
    (1982, "Thủy"), # Nhâm Tuất -> Số cuối 2 -> Thủy
    (1983, "Thủy"), # Quý Hợi -> Số cuối 3 -> Thủy
    (1994, "Hỏa"),  # Giáp Tuất -> Số cuối 4 -> Mộc (Lỗi trong logic cũ, đúng phải là Hỏa)
    (1995, "Hỏa"),  # Ất Hợi -> Số cuối 5 -> Mộc (Lỗi trong logic cũ, đúng phải là Hỏa)
    (2006, "Thổ"),  # Bính Tuất -> Số cuối 6 -> Hỏa (Lỗi trong logic cũ, đúng phải là Thổ)
    (2007, "Thổ"),  # Đinh Hợi -> Số cuối 7 -> Hỏa (Lỗi trong logic cũ, đúng phải là Thổ)
    (1988, "Mộc"),  # Mậu Thìn -> Số cuối 8 -> Thổ (Lỗi trong logic cũ, đúng phải là Mộc)
    (1989, "Mộc"),  # Kỷ Tỵ -> Số cuối 9 -> Thổ (Lỗi trong logic cũ, đúng phải là Mộc)
    (1899, None),   # Năm không hợp lệ
    ("abc", None),  # Kiểu dữ liệu không hợp lệ
])
def test_calculate_menh(birth_year, expected_menh):
    """
    KỊCH BẢN: Kiểm tra tính toán Mệnh Ngũ Hành với nhiều năm sinh khác nhau.
    Lưu ý: Logic tính Mệnh theo Thiên Can của bạn có vẻ chưa chính xác hoàn toàn.
    Test này sẽ kiểm tra theo logic hiện tại của bạn.
    """
    assert fengshui.calculate_menh(birth_year) == expected_menh

# ==============================================================================
# TEST CHO HÀM: analyze_feng_shui_rules
# ==============================================================================

# Chúng ta cần mock hàm _load_feng_shui_rules để cung cấp dữ liệu giả lập
@patch('landifys.func.fengshui._load_feng_shui_rules')
def test_analyze_feng_shui_rules(mock_load_rules):
    """
    KỊCH BẢN: Kiểm tra logic phân tích phong thủy dựa trên dữ liệu giả lập.
    """
    # ARRANGE: Cung cấp dữ liệu giả cho file fengshui.json
    mock_load_rules.return_value = {
        "direction_elements": {"Đông": "Mộc", "Nam": "Hỏa", "Tây": "Kim"},
        "relationship_rules": {"good": "Tương sinh", "neutral": "Tương hợp", "bad": "Tương khắc"},
        "feng_shui_rules": {
            "Kim": {
                "good": ["Tây"],      # Kim hợp Kim (Tương hợp, nhưng giả sử là Tốt)
                "neutral": ["Đông"],   # Kim khắc Mộc (Tương khắc, nhưng giả sử là Trung bình)
                "bad": ["Nam"]       # Hỏa khắc Kim (Tương khắc, là Xấu)
            }
        }
    }

    # ACT & ASSERT: Kiểm tra các trường hợp
    # 1. Tốt (good)
    result_good = fengshui.analyze_feng_shui_rules(user_menh="Kim", property_direction="Tây")
    assert result_good['score'] == 95
    assert "Tương sinh" in result_good['analysis']

    # 2. Trung bình (neutral)
    result_neutral = fengshui.analyze_feng_shui_rules(user_menh="Kim", property_direction="Đông")
    assert result_neutral['score'] == 75
    assert "Tương hợp" in result_neutral['analysis']

    # 3. Xấu (bad)
    result_bad = fengshui.analyze_feng_shui_rules(user_menh="Kim", property_direction="Nam")
    assert result_bad['score'] == 30
    assert "Tương khắc" in result_bad['analysis']