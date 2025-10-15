# landifys/tests/conftest.py
import os
import sys

import pytest
from pytest_factoryboy import register

from . import factories
from .factories import *

register(factories.UserFactory)
register(factories.UserProfileFactory)
register(factories.CityFactory)
register(factories.DistrictFactory)
register(factories.WardFactory)
register(factories.LocationFactory)
register(factories.PropertyTypeFactory)
register(factories.PropertyFactory)
register(factories.PropertyMediaFactory)
register(factories.ListingTypeFactory)
register(factories.UnitPriceFactory)
register(factories.ListingFactory)
register(factories.BuySellDetailFactory)
register(factories.RentalDetailFactory)
register(factories.ProjectDetailFactory)
register(factories.ReviewFactory)
register(factories.WishlistFactory)
register(factories.AppointmentFactory)
register(factories.PostFactory)
register(factories.CommentFactory)
register(factories.ReactionFactory)
register(factories.ReportFactory)
register(factories.ProtestFactory)


@pytest.fixture
def address_data(city_factory, district_factory, ward_factory):
    """Fixture tiện lợi để tạo sẵn bộ địa chỉ."""
    city = city_factory(name="TP. Hồ Chí Minh", slug="hcm")
    district = district_factory(name="Quận 1", city=city)
    ward = ward_factory(name="Phường Bến Nghé", district=district)
    return city, district, ward


def pytest_addoption(parser):
    """Thêm tùy chọn --show-steps vào dòng lệnh của pytest."""
    parser.addoption(
        "--show-steps", action="store_true", default=False, help="In ra các bước chi tiết trong test case"
    )


def pytest_runtest_protocol(item, nextitem):
    """
    Một "hook" của pytest, chạy trước và sau mỗi test case.
    Chúng ta sẽ dùng nó để in ra tên hàm và kịch bản.
    """
    # Kiểm tra xem test case có được đánh dấu bằng marker 'step_log' không
    if "step_log" in item.keywords and item.config.getoption("--show-steps"):
        # In ra thông tin trước khi chạy test
        print(f"\n\n===== TEST CASE: {item.name} =====")
        if item.obj.__doc__:
            print(f"----- KỊCH BẢN -----\n{item.obj.__doc__.strip()}")
        print("----- CÁC BƯỚC THỰC HIỆN -----")

    # Dòng này để pytest tiếp tục chạy test case như bình thường
    return None  # Chuyển quyền cho hook tiếp theo


@pytest.fixture
def log_step(request):
    """
    Tạo một fixture (giống như một dependency) có thể được inject vào test.
    Nó trả về một hàm, hàm này chỉ in ra thông điệp nếu flag --show-steps được bật.
    """
    show_steps = request.config.getoption("--show-steps")

    def _log_step_printer(message):
        if show_steps:
            print(f"  -> {message}")

    return _log_step_printer
