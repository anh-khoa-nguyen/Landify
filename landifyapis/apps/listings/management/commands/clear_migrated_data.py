from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
import sys

# Import các model có liên quan
from apps.users.models import User
# Mặc dù không xóa trực tiếp, import để in ra số lượng cho rõ ràng
from apps.listings.models import Listing
from apps.properties.models import Property


class Command(BaseCommand):
    help = (
        'AN TOÀN: Xóa dữ liệu đã được di chuyển. '
        'Chỉ xóa user có username giống hệt phone_number và không phải là admin.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Bỏ qua bước xác nhận và thực hiện xóa ngay lập tức.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("--- BẮT ĐẦU QUÁ TRÌNH XÓA DỮ LIỆU ĐÃ DI CHUYỂN (PHIÊN BẢN AN TOÀN) ---"))

        # 1. Xác định các User được tạo bởi script di chuyển
        # Dấu vân tay: username giống hệt phone_number VÀ không phải là staff/superuser.
        migrated_users_qs = User.objects.filter(
            is_superuser=False,
            is_staff=False,
            username=F('phone_number')
        )

        user_count = migrated_users_qs.count()

        if user_count == 0:
            self.stdout.write(
                self.style.SUCCESS("Không tìm thấy user nào do script tạo ra để xóa. CSDL của bạn đã sạch."))
            sys.exit()

        self.stdout.write(f"Tìm thấy {user_count} user có vẻ như được tạo bởi script di chuyển.")

        # Đếm các đối tượng liên quan sẽ bị xóa để người dùng biết
        property_count = Property.objects.filter(owner__in=migrated_users_qs).count()
        listing_count = Listing.objects.filter(user__in=migrated_users_qs).count()

        self.stdout.write(self.style.WARNING(
            f"Hành động này sẽ xóa {user_count} user, {property_count} property, và {listing_count} listing liên quan."))
        self.stdout.write(self.style.WARNING(
            "Toàn bộ dữ liệu liên quan (hồ sơ, địa chỉ, tin đăng,...) của các user này sẽ bị xóa vĩnh viễn."))

        # 2. Bước xác nhận để tránh xóa nhầm
        if not options['yes']:
            confirmation = input("Bạn có chắc chắn muốn tiếp tục? (yes/no): ")
            if confirmation.lower() != 'yes':
                self.stdout.write(self.style.ERROR("Hành động đã được hủy bỏ."))
                sys.exit()

        # 3. Thực hiện xóa
        self.stdout.write("Đang tiến hành xóa...")

        # Khi xóa User, tất cả các model liên quan có on_delete=CASCADE sẽ tự động bị xóa theo
        # (UserProfile, Property, Listing, Review, Comment, v.v.)
        deleted_count, deleted_details = migrated_users_qs.delete()

        self.stdout.write(self.style.SUCCESS(f"\n--- HOÀN TẤT VIỆC DỌN DẸP DỮ LIỆU ---"))
        self.stdout.write(
            self.style.SUCCESS(f"Đã xóa thành công {deleted_count} đối tượng chính và các dữ liệu liên quan."))
        self.stdout.write("CSDL đã sẵn sàng để chạy lại script di chuyển.")