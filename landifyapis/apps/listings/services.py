from typing import IO, Any, Dict, List

import cloudinary
import cloudinary.uploader
from django.db import transaction
from datetime import datetime, timedelta
from django.utils import timezone

from . import models, serializers
from apps.common.tasks import listings as listing_tasks
from apps.common.services import BusinessLogicError, ProtestResolutionError
from apps.properties import models as property_models # Import toàn bộ app properties
from . import models as listing_models # Import app listings (đổi tên để tránh nhầm lẫn)

import logging

from .models import PromotionRule, UserPromotion
from ..properties.models import PropertyFeature

logger = logging.getLogger(__name__)

def create_full_listing(*, user: property_models.User, validated_data: dict) -> listing_models.Listing:
    """
    Tạo một tin đăng hoàn chỉnh, bao gồm cả việc tạo mới Property nếu cần.
    Hàm này được gọi bởi ListingCreateSerializer.
    """

    # 1. Tách các dữ liệu lồng nhau ra khỏi validated_data
    property_id = validated_data.pop("property_id", None)
    property_data = validated_data.pop("property", None)

    buysell_detail_data = validated_data.pop("buysell_detail", None)
    rental_detail_data = validated_data.pop("rental_detail", None)
    project_detail_data = validated_data.pop("project_detail", None)
    features_data = validated_data.pop("features", None)
    vip_package_data = validated_data.pop("vip_package", None)
    promotion_code = validated_data.pop("promotion_code", None)

    with transaction.atomic():
        property_obj = None

        # Kịch bản 1: Người dùng cung cấp property_id để liên kết BĐS đã có
        if property_id:
            property_obj = property_id  # DRF đã chuyển nó thành object Property
            if property_obj.owner != user:
                raise BusinessLogicError("Bạn không có quyền đăng tin cho bất động sản này.")

        # Kịch bản 2: Người dùng cung cấp dữ liệu để tạo BĐS mới
        elif property_data:
            # Tách dữ liệu location lồng nhau ra
            location_data = property_data.pop("location")

            # === THAY ĐỔI 2: SỬ DỤNG MODEL TỪ APP PROPERTIES ===
            location_obj = property_models.Location.objects.create(**location_data)

            # Tạo Property mới với owner là người dùng hiện tại
            property_obj = property_models.Property.objects.create(
                owner=user,
                location=location_obj,
                **property_data
            )

        # Nếu không có kịch bản nào xảy ra, ném lỗi
        if not property_obj:
            raise BusinessLogicError(
                "Không thể xác định hoặc tạo mới bất động sản. Vui lòng cung cấp 'property' hoặc 'property_id'.")

        # 3. Tạo đối tượng Listing chính
        #    `validated_data` lúc này chỉ còn chứa các trường của Listing (title, content...)
        listing = listing_models.Listing.objects.create(user=user, property=property_obj, **validated_data)

        if vip_package_data:
            # Gọi một hàm helper mới để xử lý logic VIP
            _update_or_create_vip_status(
                listing=listing,
                vip_package_data=vip_package_data
            )

        if promotion_code:
            promo_to_use = UserPromotion.objects.get(code=promotion_code, user=user)

            promo_to_use.status = UserPromotion.Status.USED
            promo_to_use.used_at = timezone.now()
            promo_to_use.used_on_listing = listing
            promo_to_use.save()

            if promo_to_use.rule.promo_type == PromotionRule.PromotionType.FREE_LISTING:
                free_days = promo_to_use.rule.free_listing_days
                if free_days:
                    print(f"Áp dụng {free_days} ngày đăng tin miễn phí cho listing {listing.id}")


        if features_data:
            feature_values_to_create = []
            # Lấy tất cả các feature cần thiết trong 1 query để tối ưu
            feature_codes = [item['feature_code'] for item in features_data]
            features_map = {f.code: f for f in PropertyFeature.objects.filter(code__in=feature_codes)}

            for item in features_data:
                feature_code = item.get('feature_code')
                feature_obj = features_map.get(feature_code)
                print(feature_code, feature_obj)

                if feature_obj:
                    # TODO: Thêm logic validate giá trị `value` ở đây nếu cần
                    feature_values_to_create.append(
                        listing_models.ListingPropertyFeatureValue(
                            listing=listing,
                            feature=feature_obj,
                            value=item.get('value')
                        )
                    )

            if feature_values_to_create:
                listing_models.ListingPropertyFeatureValue.objects.bulk_create(feature_values_to_create)

        # 4. Tạo các đối tượng chi tiết liên quan (OneToOne) nếu có
        if buysell_detail_data:
            listing_models.BuySellDetail.objects.create(listing=listing, **buysell_detail_data)

        if rental_detail_data:
            listing_models.RentalDetail.objects.create(listing=listing, **rental_detail_data)

        if project_detail_data:
            listing_models.ProjectDetail.objects.create(listing=listing, **project_detail_data)

    listing_tasks.check_listing_for_spam.delay(listing.id)

    return listing


def _update_or_create_vip_status(*, listing: listing_models.Listing, vip_package_data: dict):
    """
    Hàm helper để tạo mới hoặc gia hạn trạng thái VIP cho một tin đăng.
    Đây là nơi chứa toàn bộ logic "cộng dồn" thông minh.
    """
    vip_type = vip_package_data.get('vip_type')
    duration_days = vip_package_data.get('duration_days')
    # Mặc định ngày bắt đầu là hôm nay nếu không được cung cấp
    start_date = vip_package_data.get('start_date', timezone.localdate())

    # Chuyển start_date thành datetime có nhận biết timezone
    start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))

    # Lấy hoặc tạo mới bản ghi ListingVip cho tin đăng này
    vip_status, created = listing_models.ListingVip.objects.get_or_create(
        listing=listing,
        defaults={'vip_type': vip_type}
    )

    # Xác định ngày bắt đầu để tính toán gia hạn
    # Nếu gói VIP cũ đã hết hạn, ngày bắt đầu sẽ là ngày người dùng chọn (hoặc hôm nay)
    # Nếu gói VIP cũ vẫn còn hạn, ngày bắt đầu sẽ là ngày hết hạn của gói cũ
    base_date = timezone.now()
    if not created and vip_status.is_active:
        base_date = vip_status.end_date

    # Đảm bảo ngày bắt đầu không sớm hơn thời điểm hiện tại
    effective_start_date = max(base_date, start_datetime)

    # Tính toán ngày kết thúc mới
    new_end_date = effective_start_date + timedelta(days=duration_days)

    # Cập nhật bản ghi vip_status
    vip_status.vip_type = vip_type
    vip_status.end_date = new_end_date
    vip_status.save()

def update_listing_features(*, listing: models.Listing, features_data: List[Dict[str, Any]]):
    """
    Cập nhật (thêm/sửa/xóa) các giá trị đặc điểm cho một tin đăng.
    """

    if not isinstance(features_data, list):
        raise BusinessLogicError("Dữ liệu đặc điểm phải là một danh sách.")

    incoming_feature_ids = {item.get("feature_id") for item in features_data if item.get("feature_id")}
    features_map = {
        feature.id: feature for feature in models.PropertyFeature.objects.filter(id__in=incoming_feature_ids)
    }

    # Bắt đầu một giao dịch để đảm bảo tất cả các thay đổi thành công hoặc không gì cả
    with transaction.atomic():
        current_feature_ids = set(listing.feature_values.values_list("feature_id", flat=True))
        features_to_delete = current_feature_ids - incoming_feature_ids
        if features_to_delete:
            models.ListingPropertyFeatureValue.objects.filter(
                listing=listing, feature_id__in=features_to_delete
            ).delete()

        # 2. Thêm hoặc cập nhật các feature từ dữ liệu đầu vào
        for item in features_data:
            feature_id = item.get("feature_id")
            value = item.get("value")

            # Bỏ qua nếu thiếu dữ liệu hoặc feature_id không hợp lệ
            if not feature_id or feature_id not in features_map:
                continue

            feature = features_map[feature_id]
            validated_value = None

            # 3. Xác thực và chuẩn hóa giá trị dựa trên loại feature
            if feature.feature_type == models.PropertyFeature.FeatureType.FLOAT:
                try:
                    validated_value = float(value)
                except (ValueError, TypeError):
                    # Ghi log cảnh báo về dữ liệu không hợp lệ và bỏ qua
                    logger.warning(
                        "Giá trị '%s' không hợp lệ cho feature số thực '%s'. Bỏ qua.",
                        value, feature.name
                    )
                    continue

            elif feature.feature_type == models.PropertyFeature.FeatureType.BOOLEAN:
                # Chuyển đổi các giá trị 'true'/'false' hoặc 1/0 thành boolean
                if isinstance(value, str) and value.lower() in ["true", "1"]:
                    validated_value = True
                elif isinstance(value, str) and value.lower() in ["false", "0"]:
                    validated_value = False
                else:
                    validated_value = bool(value)

            elif feature.feature_type == models.PropertyFeature.FeatureType.DIRECTION:
                try:
                    direction_id = int(value)
                    validated_value = direction_id
                except (ValueError, TypeError):
                    print(
                        f"Cảnh báo: Giá trị '{value}' không hợp lệ cho feature hướng. Phải là một ID số nguyên. Bỏ qua."
                    )
                    continue

            else:
                validated_value = str(value).strip()

            # 4. Lưu vào CSDL
            if validated_value is not None:
                models.ListingPropertyFeatureValue.objects.update_or_create(
                    listing=listing, feature=feature, defaults={"value": validated_value}
                )