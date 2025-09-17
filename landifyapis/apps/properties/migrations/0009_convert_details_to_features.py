from django.db import migrations


def convert_details_to_features(apps, schema_editor):
    PropertyFeature = apps.get_model('properties', 'PropertyFeature')
    PropertyType = apps.get_model('properties', 'PropertyType')

    # Lấy các PropertyType cần thiết, dùng try-except để tránh lỗi nếu chưa có
    try:
        props = {pt.code: pt for pt in PropertyType.objects.all()}
        residential_types = [
            props.get('APARTMENT'), props.get('MINI_APARTMENT_SERVICE'),
            props.get('TOWNHOUSE'), props.get('VILLA'), props.get('MOTEL_ROOM')
        ]
        house_types = [
            props.get('TOWNHOUSE'), props.get('VILLA'), props.get('STREET_HOUSE')
        ]
    except Exception:
        return

    # --- TẠO CÁC FEATURE MỚI TỪ RENTALDETAIL ---
    deposit, _ = PropertyFeature.objects.get_or_create(
        code="DEPOSIT_AMOUNT", defaults={'name': "Số tiền cọc", 'category': "TECHNICAL", 'feature_type': "FLOAT"})
    deposit.applicable_property_types.set([pt for pt in residential_types if pt])

    lease_duration, _ = PropertyFeature.objects.get_or_create(
        code="MIN_LEASE_DURATION",
        defaults={'name': "Thời hạn thuê tối thiểu (tháng)", 'category': "TECHNICAL", 'feature_type': "FLOAT"})
    lease_duration.applicable_property_types.set([pt for pt in residential_types if pt])

    allow_pets, _ = PropertyFeature.objects.get_or_create(
        code="ALLOW_PETS", defaults={'name': "Cho phép thú cưng", 'category': "AMENITY", 'feature_type': "BOOLEAN"})
    allow_pets.applicable_property_types.set([pt for pt in residential_types if pt])

    # --- TẠO CÁC FEATURE MỚI TỪ BUYSELLDETAIL ---
    condition, _ = PropertyFeature.objects.get_or_create(
        code="CONDITION_STATUS", defaults={'name': "Tình trạng nhà", 'category': "TECHNICAL", 'feature_type': "TEXT"})
    condition.applicable_property_types.set([pt for pt in house_types if pt])

    is_mortgaged, _ = PropertyFeature.objects.get_or_create(
        code="IS_MORTGAGED", defaults={'name': "Đang thế chấp", 'category': "TECHNICAL", 'feature_type': "BOOLEAN"})
    is_mortgaged.applicable_property_types.set([pt for pt in house_types if pt])

    print("\nĐã tạo các PropertyFeature mới từ các model Detail cũ.")


def unpopulate(apps, schema_editor):
    PropertyFeature = apps.get_model('properties', 'PropertyFeature')
    codes_to_delete = ["DEPOSIT_AMOUNT", "MIN_LEASE_DURATION", "ALLOW_PETS", "CONDITION_STATUS", "IS_MORTGAGED"]
    PropertyFeature.objects.filter(code__in=codes_to_delete).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('properties', '0008_add_property_features_data'),  # File data migration trước đó của properties
    ]
    operations = [
        migrations.RunPython(convert_details_to_features, unpopulate),
    ]