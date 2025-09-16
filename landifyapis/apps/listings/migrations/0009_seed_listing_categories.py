from django.db import migrations


def populate_listing_categories(apps, schema_editor):
    """
    Tạo ra các cặp (ListingType, PropertyType) hợp lệ để người dùng lựa chọn.
    """
    ListingCategory = apps.get_model('listings', 'ListingCategory')
    ListingType = apps.get_model('listings', 'ListingType')
    PropertyType = apps.get_model('properties', 'PropertyType')

    # Xóa dữ liệu cũ để đảm bảo script có thể chạy lại
    ListingCategory.objects.all().delete()

    # Lấy các đối tượng gốc cần thiết
    try:
        rent_type = ListingType.objects.get(code='RENT')
        sell_type = ListingType.objects.get(code='BUY_SELL')
        project_type = ListingType.objects.get(code='PROJECT')
        # Dùng dictionary để tra cứu PropertyType cho dễ
        props = {pt.code: pt for pt in PropertyType.objects.all()}
    except (ListingType.DoesNotExist, PropertyType.DoesNotExist) as e:
        # Nếu dữ liệu gốc chưa được nạp, không làm gì cả
        print(f"Bỏ qua việc nạp ListingCategory vì thiếu dữ liệu gốc: {e}")
        return

    # --- ĐỊNH NGHĨA CÁC QUY TẮC HỢP LỆ ---

    # --- DANH MỤC CHO THUÊ ---
    rent_categories = [
        'APARTMENT', 'MINI_APARTMENT_SERVICE', 'TOWNHOUSE', 'VILLA',
        'STREET_HOUSE', 'SHOPHOUSE', 'MOTEL_ROOM', 'OFFICE', 'KIOSK',
        'WAREHOUSE', 'OTHER_REAL_ESTATE'
    ]
    for code in rent_categories:
        if code in props:
            ListingCategory.objects.create(listing_type=rent_type, property_type=props[code])

    # --- DANH MỤC MUA BÁN ---
    sell_categories = [
        'APARTMENT', 'MINI_APARTMENT_SERVICE', 'TOWNHOUSE', 'VILLA',
        'STREET_HOUSE', 'SHOPHOUSE', 'LAND', 'FARM_RESORT', 'CONDO',
        'WAREHOUSE', 'OTHER_REAL_ESTATE'
    ]
    for code in sell_categories:
        if code in props:
            ListingCategory.objects.create(listing_type=sell_type, property_type=props[code])

    # --- DANH MỤC DỰ ÁN ---
    project_categories = [
        'APARTMENT', 'LAND', 'VILLA', 'SHOPHOUSE'
    ]
    for code in project_categories:
        if code in props:
            ListingCategory.objects.create(listing_type=project_type, property_type=props[code])

    print(f"\nĐã tạo {ListingCategory.objects.count()} danh mục đăng tin hợp lệ.")


def unpopulate_categories(apps, schema_editor):
    """Hàm rollback, xóa dữ liệu đã tạo."""
    ListingCategory = apps.get_model('listings', 'ListingCategory')
    ListingCategory.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('listings', '0008_listingcategory'),  # <-- Tên file migration bạn vừa tạo ở Bước 2
        ('properties', '0005_initial_properties_data'),  # File data migration của properties
    ]

    operations = [
        migrations.RunPython(populate_listing_categories, unpopulate_categories),
    ]