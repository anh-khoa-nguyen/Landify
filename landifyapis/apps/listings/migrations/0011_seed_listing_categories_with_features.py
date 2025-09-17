from django.db import migrations

def populate_listing_categories(apps, schema_editor):
    ListingCategory = apps.get_model('listings', 'ListingCategory')
    ListingType = apps.get_model('listings', 'ListingType')
    PropertyType = apps.get_model('properties', 'PropertyType')
    PropertyFeature = apps.get_model('properties', 'PropertyFeature')

    ListingCategory.objects.all().delete()

    try:
        rent_type = ListingType.objects.get(code='RENT')
        sell_type = ListingType.objects.get(code='BUY_SELL')
        props = {pt.code: pt for pt in PropertyType.objects.all()}
        features = {pf.code: pf for pf in PropertyFeature.objects.all()}
    except Exception as e:
        print(f"\nBỏ qua vì thiếu dữ liệu gốc: {e}")
        return

    # --- ĐỊNH NGHĨA QUY TẮC ---

    # --- Cho thuê Nhà riêng ---
    cat_rent_townhouse = ListingCategory.objects.create(listing_type=rent_type, property_type=props['TOWNHOUSE'])
    rent_townhouse_features = [
        features.get('NUM_BEDROOMS'), features.get('NUM_BATHROOMS'), features.get('DEPOSIT_AMOUNT'), 
        features.get('MIN_LEASE_DURATION'), features.get('ALLOW_PETS')
    ]
    cat_rent_townhouse.applicable_features.set([f for f in rent_townhouse_features if f])

    # --- Bán Nhà riêng ---
    cat_sell_townhouse = ListingCategory.objects.create(listing_type=sell_type, property_type=props['TOWNHOUSE'])
    sell_townhouse_features = [
        features.get('NUM_BEDROOMS'), features.get('NUM_BATHROOMS'), features.get('CONDITION_STATUS'), 
        features.get('IS_MORTGAGED')
    ]
    cat_sell_townhouse.applicable_features.set([f for f in sell_townhouse_features if f])

    # --- Bán Đất ---
    cat_sell_land = ListingCategory.objects.create(listing_type=sell_type, property_type=props['LAND'])

    print(f"\nĐã tạo {ListingCategory.objects.count()} danh mục đăng tin hợp lệ với các quy tắc feature.")

def unpopulate_categories(apps, schema_editor):
    ListingCategory = apps.get_model('listings', 'ListingCategory')
    ListingCategory.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('listings', '0010_remove_projectdetail_listing_and_more'), # File migration đã tạo ListingCategory
        ('properties', '0009_convert_details_to_features'), # File migration đã tạo các feature mới
    ]
    operations = [
        migrations.RunPython(populate_listing_categories, unpopulate_categories),
    ]