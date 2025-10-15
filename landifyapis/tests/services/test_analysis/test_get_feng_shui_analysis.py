from datetime import date
from unittest.mock import patch

import pytest
from landifys.services import BusinessLogicError, analysis


# Mock toàn bộ module func.fengshui
@patch("landifys.services.analysis.fengshui")
@pytest.mark.step_log
def test_get_feng_shui_analysis_successfully(mock_fengshui, log_step):
    """
    KỊCH BẢN: Thành công
    Kiểm tra service gọi đúng các hàm fengshui và trả về kết quả đúng định dạng.
    """
    log_step("ARRANGE: Cấu hình các giá trị trả về giả lập từ module fengshui.")
    mock_fengshui.calculate_menh.return_value = "Kim"
    mock_fengshui.analyze_feng_shui_rules.return_value = {"score": 95, "analysis": "Phân tích chi tiết..."}

    log_step("ARRANGE: Chuẩn bị dữ liệu đầu vào cho service.")
    direction = "Tây Bắc"
    dob = date(1990, 1, 1)

    log_step("ACT: Gọi service get_feng_shui_analysis.")
    result = analysis.get_feng_shui_analysis(property_direction_name=direction, date_of_birth=dob)

    log_step("ASSERT: Hàm calculate_menh được gọi với đúng năm sinh.")
    mock_fengshui.calculate_menh.assert_called_once_with(birth_year=1990)

    log_step("ASSERT: Hàm analyze_feng_shui_rules được gọi với đúng Mệnh và Hướng.")
    mock_fengshui.analyze_feng_shui_rules.assert_called_once_with(user_menh="Kim", property_direction=direction)

    log_step("ASSERT: Kết quả trả về từ service có đúng định dạng và dữ liệu.")
    expected_result = {
        "user_menh_element": "Kim",
        "property_direction": direction,
        "compatibility_score": 95,
        "analysis": "Phân tích chi tiết...",
    }
    assert result == expected_result
    log_step("=> PASSED!")


@patch("landifys.services.analysis.fengshui")
@pytest.mark.step_log
def test_get_feng_shui_analysis_fails_if_menh_not_found(mock_fengshui, log_step):
    """
    KỊCH BẢN: Thất bại - Không thể xác định Mệnh cho năm sinh.
    """
    log_step("ARRANGE: Cấu hình mock calculate_menh trả về None.")
    mock_fengshui.calculate_menh.return_value = None

    log_step("ACT & ASSERT: Gọi service và kiểm tra exception.")
    with pytest.raises(BusinessLogicError, match="Không thể xác định Mệnh cho năm sinh 1990."):
        analysis.get_feng_shui_analysis(property_direction_name="Đông", date_of_birth=date(1990, 1, 1))
    log_step("=> PASSED!")
