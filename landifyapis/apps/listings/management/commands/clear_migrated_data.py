import sys

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, F, Q  # <<< THÊM IMPORT Q

from apps.listings.models import Listing, ListingCategory, ListingType
from apps.properties.models import Location, Property, PropertyType

# Import các model có liên quan
from apps.users.models import User


class Command(BaseCommand):
    help = (
        "AN TOÀN: Xóa dữ liệu Nhà trọ/Phòng trọ cũ và đã được di chuyển từ script."
        "Bao gồm cả các tin đăng có listing_category=NULL."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Bỏ qua bước xác nhận và thực hiện xóa ngay lập tức.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("--- BẮT ĐẦU QUÁ TRÌNH XÓA DỮ LIỆU NHÀ TRỌ/PHÒNG TRỌ ---"))

        # 1. Lấy các đối tượng gốc cần thiết để xác định dữ liệu cần xóa
        try:
            property_type_motel = PropertyType.objects.get(code="MOTEL_ROOM")
            listing_type_rent = ListingType.objects.get(code="RENT")
            # ListingCategory có thể có hoặc không, không làm script dừng lại
            motel_rent_category = ListingCategory.objects.filter(
                listing_type=listing_type_rent, property_type=property_type_motel
            ).first()
        except (PropertyType.DoesNotExist, ListingType.DoesNotExist):
            self.stdout.write(
                self.style.ERROR(
                    "Không tìm thấy PropertyType 'MOTEL_ROOM' hoặc ListingType 'RENT'. Không thể tiếp tục."
                )
            )
            sys.exit()

        # ====================================================================
        # === LOGIC MỚI: TÌM KIẾM TIN ĐĂNG CẦN XÓA BẰNG CẢ 2 CÁCH ===
        # ====================================================================

        # Điều kiện 1: Tìm các tin đăng cũ có listing_category là NULL
        # nhưng liên kết đến Property có type là MOTEL_ROOM
        condition_old_data = Q(listing_category__isnull=True, property__property_type=property_type_motel)

        # Điều kiện 2: Tìm các tin đăng mới đã được gán category chính xác
        condition_new_data = Q()  # Khởi tạo một Q object rỗng
        if motel_rent_category:
            condition_new_data = Q(listing_category=motel_rent_category)

        # Kết hợp cả hai điều kiện bằng phép toán OR (|)
        migrated_listings_qs = Listing.objects.filter(condition_old_data | condition_new_data).distinct()

        # ====================================================================

        listing_count = migrated_listings_qs.count()

        if listing_count == 0:
            self.stdout.write(
                self.style.SUCCESS("Không tìm thấy tin đăng Nhà trọ/Phòng trọ nào cần dọn dẹp. CSDL của bạn đã sạch.")
            )
            sys.exit()

        self.stdout.write(
            f"Tìm thấy {listing_count} tin đăng Nhà trọ/Phòng trọ (bao gồm cả dữ liệu cũ và mới) cần dọn dẹp."
        )

        # 3. Thu thập các ID liên quan để xóa (Phần này giữ nguyên)
        property_ids_to_delete = set(migrated_listings_qs.values_list("property_id", flat=True))

        # Sửa logic tìm user để nó an toàn hơn, tránh lỗi listing_count không khớp
        user_ids_to_delete = set(
            migrated_listings_qs.filter(user__username=F("user__phone_number")).values_list("user_id", flat=True)
        )

        final_user_ids_to_delete = set()
        users_to_check = User.objects.filter(id__in=user_ids_to_delete).annotate(
            total_listings=Count("listings"),
            motel_listings=Count("listings", filter=Q(listings__in=migrated_listings_qs)),
        )

        # Chỉ xóa những user mà TOÀN BỘ tin đăng của họ đều là tin motel cần xóa
        for user in users_to_check:
            if user.total_listings == user.motel_listings:
                final_user_ids_to_delete.add(user.id)

        location_ids_to_delete = set(
            Property.objects.filter(id__in=property_ids_to_delete).values_list("location_id", flat=True)
        )

        property_count = len(property_ids_to_delete)
        user_count = len(final_user_ids_to_delete)
        location_count = len(location_ids_to_delete)

        self.stdout.write(
            self.style.WARNING(
                f"Hành động này sẽ xóa: {listing_count} tin đăng, {property_count} bất động sản, "
                f"{location_count} địa điểm, và {user_count} người dùng liên quan."
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "Toàn bộ dữ liệu liên quan (hồ sơ, media,...) của các đối tượng này sẽ bị xóa vĩnh viễn."
            )
        )

        # 4. Bước xác nhận (Giữ nguyên)
        # 4. Bước xác nhận
        if not options["yes"]:
            confirmation = input("Bạn có chắc chắn muốn tiếp tục? (yes/no): ")
            if confirmation.lower() != "yes":
                self.stdout.write(self.style.ERROR("Hành động đã được hủy bỏ."))
                sys.exit()

        # 5. Thực hiện xóa theo thứ tự an toàn (từ con đến cha)
        self.stdout.write("Đang tiến hành xóa...")

        # ====================================================================
        # === BẮT ĐẦU SỬA LỖI TẠI ĐÂY ===
        # ====================================================================

        # Lấy queryset cho các đối tượng liên quan TRƯỚC KHI xóa
        properties_to_delete_qs = Property.objects.filter(id__in=property_ids_to_delete)
        locations_to_delete_qs = Location.objects.filter(id__in=location_ids_to_delete)
        users_to_delete_qs = User.objects.filter(id__in=final_user_ids_to_delete)

        # Xóa theo thứ tự an toàn
        migrated_listings_qs.delete()
        properties_to_delete_qs.delete()
        locations_to_delete_qs.delete()
        users_to_delete_qs.delete()

        self.stdout.write(self.style.SUCCESS(f"\n--- HOÀN TẤT VIỆC DỌN DẸP DỮ LIỆU ---"))
        # Sử dụng các biến đếm đã có từ trước để hiển thị thông báo
        self.stdout.write(
            f"Đã xóa: {listing_count} tin đăng, "
            f"{property_count} BĐS, "
            f"{location_count} địa điểm, "
            f"{user_count} người dùng."
        )
        self.stdout.write("CSDL đã sẵn sàng để chạy lại script di chuyển.")
