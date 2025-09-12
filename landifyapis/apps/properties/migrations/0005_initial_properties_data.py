# D:\Backend\Landify\landifyapis\apps\properties\migrations\0005_initial_properties_data.py

from django.db import migrations

# Danh sách các model trong app 'properties' cần seed data
MODEL_NAMES = ["PropertyType", "Direction", "LegalStatus",]

def populate_properties_data(apps, schema_editor):
    """
    Tạo dữ liệu ban đầu cho các model trong app 'properties'.
    """
    PropertyType = apps.get_model('properties', 'PropertyType')
    Direction = apps.get_model('properties', 'Direction')
    LegalStatus = apps.get_model('properties', 'LegalStatus')

    # --- Xóa dữ liệu cũ ---
    for model_name in MODEL_NAMES:
        Model = apps.get_model('properties', model_name)
        Model.objects.all().delete()
        print(f"\nDeleted all existing records from properties.{model_name}.")

    # --- Tạo dữ liệu mới ---
    PropertyType.objects.bulk_create([
        PropertyType(name="Căn hộ", code="APARTMENT"),
        PropertyType(name="Nhà phố", code="TOWNHOUSE"),
        PropertyType(name="Đất nền", code="LAND"),
        PropertyType(name="Văn phòng", code="OFFICE"),
        PropertyType(name="Biệt thự", code="VILLA"),
        PropertyType(name="Phòng trọ", code="MOTEL_ROOM"),
        PropertyType(name="Kho, xưởng", code="WAREHOUSE"),
    ])
    print("Created PropertyType records.")

    Direction.objects.bulk_create([
        Direction(name="Đông", code="EAST", element="Mộc"),
        Direction(name="Tây", code="WEST", element="Kim"),
        Direction(name="Nam", code="SOUTH", element="Hỏa"),
        Direction(name="Bắc", code="NORTH", element="Thủy"),
        Direction(name="Đông Nam", code="SOUTHEAST", element="Mộc"),
        Direction(name="Tây Bắc", code="NORTHWEST", element="Kim"),
        Direction(name="Đông Bắc", code="NORTHEAST", element="Thổ"),
        Direction(name="Tây Nam", code="SOUTHWEST", element="Thổ"),
    ])
    print("Created Direction records.")

    LegalStatus.objects.bulk_create([
        LegalStatus(name="Sổ hồng", code="SOHONG"),
        LegalStatus(name="Sổ đỏ", code="SODO"),
        LegalStatus(name="Hợp đồng mua bán", code="HDMB"),
        LegalStatus(name="Giấy tờ khác", code="OTHER"),
    ])
    print("Created LegalStatus records.")

def unpopulate_properties_data(apps, schema_editor):
    """
    Hàm rollback, xóa dữ liệu đã tạo.
    """
    for model_name in MODEL_NAMES:
        Model = apps.get_model('properties', model_name)
        Model.objects.all().delete()
        print(f"\nDeleted all records from properties.{model_name} during rollback.")


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0004_direction_code_legalstatus_code'), # Phụ thuộc vào migration tạo bảng/cột gần nhất của app 'properties'
    ]

    operations = [
        migrations.RunPython(populate_properties_data, unpopulate_properties_data),
    ]