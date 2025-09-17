from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, F
import sys

# Import các model có liên quan
from apps.users.models import User
from apps.listings.models import Listing, ListingCategory, ListingType
from apps.properties.models import Property, PropertyType, Location


class Command(BaseCommand):
    help = (
        'AN TOÀN: Xóa dữ liệu Nhà trọ/Phòng trọ đã được di chuyển từ script.'
        'Chỉ xóa các Listing, Property, và User liên quan đến danh mục "Cho Thuê Nhà trọ, phòng trọ".'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Bỏ qua bước xác nhận và thực hiện xóa ngay lập tức.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("--- BẮT ĐẦU QUÁ TRÌNH XÓA DỮ LIỆU NHÀ TRỌ/PHÒNG TRỌ ĐÃ DI CHUYỂN ---"))

        # 1. Xác định "dấu vân tay" gốc: ListingCategory "Cho Thuê Nhà trọ, phòng trọ"
        try:
            property_type_motel = PropertyType.objects.get(code='MOTEL_ROOM')
            listing_type_rent = ListingType.objects.get(code='RENT')
            motel_rent_category = ListingCategory.objects.get(
                listing_type=listing_type_rent,
                property_type=property_type_motel
            )
        except (PropertyType.DoesNotExist, ListingType.DoesNotExist, ListingCategory.DoesNotExist):
            self.stdout.write(
                self.style.ERROR("Không tìm thấy ListingCategory 'Cho Thuê Nhà trọ, phòng trọ'. Không có gì để xóa."))
            sys.exit()

        # 2. Tìm tất cả các Listing thuộc về category này
        migrated_listings_qs = Listing.objects.filter(listing_category=motel_rent_category)
        listing_count = migrated_listings_qs.count()

        if listing_count == 0:
            self.stdout.write(self.style.SUCCESS(
                "Không tìm thấy tin đăng Nhà trọ/Phòng trọ nào do script tạo ra. CSDL của bạn đã sạch."))
            sys.exit()

        self.stdout.write(
            f"Tìm thấy {listing_count} tin đăng Nhà trọ/Phòng trọ có vẻ như được tạo bởi script di chuyển.")

        # 3. Thu thập các ID liên quan để xóa
        property_ids_to_delete = set(migrated_listings_qs.values_list('property_id', flat=True))

        # Chỉ thu thập các User có username giống phone_number để tăng độ an toàn
        user_ids_to_delete = set(
            migrated_listings_qs.filter(user__username=F('user__phone_number'))
            .values_list('user_id', flat=True)
        )

        # Tìm các User mà tất cả các tin đăng của họ đều là tin di chuyển
        # (Để tránh xóa User đã đăng cả tin di chuyển và tin thật)
        users_to_check = User.objects.filter(id__in=user_ids_to_delete).annotate(
            total_listings=Count('listings')
        )
        final_user_ids_to_delete = {
            user.id for user in users_to_check if user.total_listings == listing_count
        }

        # Thu thập Location IDs từ các Property sắp bị xóa
        location_ids_to_delete = set(
            Property.objects.filter(id__in=property_ids_to_delete)
            .values_list('location_id', flat=True)
        )

        property_count = len(property_ids_to_delete)
        user_count = len(final_user_ids_to_delete)
        location_count = len(location_ids_to_delete)

        self.stdout.write(self.style.WARNING(
            f"Hành động này sẽ xóa: {listing_count} tin đăng, {property_count} bất động sản, "
            f"{location_count} địa điểm, và {user_count} người dùng liên quan."
        ))
        self.stdout.write(self.style.WARNING(
            "Toàn bộ dữ liệu liên quan (hồ sơ, media,...) của các đối tượng này sẽ bị xóa vĩnh viễn."
        ))

        # 4. Bước xác nhận
        if not options['yes']:
            confirmation = input("Bạn có chắc chắn muốn tiếp tục? (yes/no): ")
            if confirmation.lower() != 'yes':
                self.stdout.write(self.style.ERROR("Hành động đã được hủy bỏ."))
                sys.exit()

        # 5. Thực hiện xóa theo thứ tự an toàn (từ con đến cha)
        self.stdout.write("Đang tiến hành xóa...")

        # Xóa Listings -> Xóa Properties -> Xóa Locations -> Xóa Users
        deleted_listings, _ = migrated_listings_qs.delete()
        deleted_properties, _ = Property.objects.filter(id__in=property_ids_to_delete).delete()
        deleted_locations, _ = Location.objects.filter(id__in=location_ids_to_delete).delete()
        deleted_users, _ = User.objects.filter(id__in=final_user_ids_to_delete).delete()

        self.stdout.write(self.style.SUCCESS(f"\n--- HOÀN TẤT VIỆC DỌN DẸP DỮ LIỆU ---"))
        self.stdout.write(
            f"Đã xóa: {deleted_listings.get('listings.Listing', 0)} tin đăng, "
            f"{deleted_properties.get('properties.Property', 0)} BĐS, "
            f"{deleted_locations.get('properties.Location', 0)} địa điểm, "
            f"{deleted_users.get('users.User', 0)} người dùng."
        )
        self.stdout.write("CSDL đã sẵn sàng để chạy lại script di chuyển.")