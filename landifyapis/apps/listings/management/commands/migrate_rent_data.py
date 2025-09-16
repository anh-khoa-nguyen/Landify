import re
from datetime import datetime
import unicodedata

from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.contrib.gis.geos import Point

from apps.users.models import User, UserProfile
from apps.properties.models import Location, Property, PropertyType
from apps.listings.models import Listing, ListingType, UnitPrice
from vi_address.models import Ward

def normalize_string(s):
    if not s: return ""
    s = str(s).lower().strip()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    prefixes = ['phuong ', 'xa ', 'quan ', 'huyen ', 'thanh pho ', 'tp ', 'tinh ']
    for prefix in prefixes:
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s.strip()


def find_best_ward_match(city_str, district_str, ward_str, preloaded_wards):
    if not city_str or not district_str or not ward_str: return None
    norm_city_old = normalize_string(city_str)
    norm_district_old = normalize_string(district_str)
    norm_ward_old = normalize_string(ward_str)
    for ward_obj, normalized_names_new in preloaded_wards.items():
        if (normalized_names_new['ward'] == norm_ward_old and
                normalized_names_new['district'] == norm_district_old and
                normalized_names_new['city'] == norm_city_old):
            return ward_obj
    potential_matches = []
    for ward_obj, normalized_names_new in preloaded_wards.items():
        if (norm_district_old in normalized_names_new['district'] and
                norm_city_old in normalized_names_new['city'] and
                norm_ward_old in normalized_names_new['ward']):
            potential_matches.append(ward_obj)
    if len(potential_matches) == 1: return potential_matches[0]
    return None


def parse_price(price_str, unit_str):
    if not price_str or not unit_str: return None, None
    try:
        price_value = float(re.sub(r'[^\d.]', '', str(price_str).replace(',', '.')))
        if "triệu" in unit_str:
            price_value *= 1_000_000
        elif "tỷ" in unit_str:
            price_value *= 1_000_000_000
        unit_obj = UnitPrice.objects.get(code='PER_MONTH')
        return price_value, unit_obj
    except (ValueError, TypeError, UnitPrice.DoesNotExist):
        return None, None


class Command(BaseCommand):
    help = 'Migrates CORE data from the legacy MySQL database with detailed debugging for location.'

    def _generate_full_phone_number(self, masked_phone):
        if not masked_phone or not isinstance(masked_phone, str): return None
        phone_str = masked_phone.strip()
        if "***" in phone_str:
            sequential_digits = f"{self.phone_counter:03d}"
            phone_str = phone_str.replace("***", sequential_digits)
            self.phone_counter += 1
        return re.sub(r'\D', '', phone_str)

    def handle(self, *args, **options):
        self.phone_counter = 1
        self.stdout.write(self.style.SUCCESS("--- Bắt đầu di chuyển dữ liệu CỐT LÕI (CHẾ ĐỘ DEBUG) ---"))
        self.stdout.write("Đang tải trước dữ liệu lookup...")

        preloaded_wards = {
            w: {'city': normalize_string(w.parent_code.parent_code.name),
                'district': normalize_string(w.parent_code.name), 'ward': normalize_string(w.name)}
            for w in Ward.objects.select_related('parent_code__parent_code').all()
        }
        property_type_motel = PropertyType.objects.get(code='MOTEL_ROOM')
        listing_type_rent = ListingType.objects.get(code='RENT')

        migrated_count = 0
        skipped_count = 0

        with connections['legacy_mysql'].cursor() as cursor:
            query = "SELECT * FROM `details_rent_nha-tro-phong-tro`"
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]

            for row in cursor.fetchall():
                source_data = dict(zip(columns, row))
                source_property_id = source_data.get('property_id')

                if Listing.objects.filter(property_id=source_property_id).exists():
                    skipped_count += 1
                    continue

                try:
                    with transaction.atomic():
                        # ... (Phần xử lý User giữ nguyên) ...
                        raw_phone = source_data.get('phone')
                        phone_number = self._generate_full_phone_number(raw_phone)
                        if not phone_number or len(phone_number) < 9:
                            skipped_count += 1
                            continue
                        user, user_created = User.objects.get_or_create(phone_number=phone_number,
                                                                        defaults={'username': phone_number,
                                                                                  'first_name': source_data.get(
                                                                                      'name_per', 'Người dùng')})
                        if user_created: UserProfile.objects.create(user=user)
                        ward_obj = find_best_ward_match(source_data.get('city'), source_data.get('district'),
                                                        source_data.get('ward'), preloaded_wards)
                        if not ward_obj:
                            skipped_count += 1
                            continue

                        # ==========================================================
                        # <<< KHỐI DEBUG BẮT ĐẦU TỪ ĐÂY >>>
                        # ==========================================================
                        self.stdout.write(f"\n--- [DEBUG] Đang xử lý tin {source_property_id} ---")

                        lat_val = source_data.get('lat')
                        lng_val = source_data.get('lng')

                        self.stdout.write(
                            f"  - Giá trị đọc từ CSDL cũ: lat='{lat_val}' (kiểu: {type(lat_val)}), lng='{lng_val}' (kiểu: {type(lng_val)})")

                        point_obj = None
                        # Kiểm tra kỹ hơn: không chỉ tồn tại mà còn không phải là chuỗi rỗng
                        if lat_val and str(lat_val).strip() and lng_val and str(lng_val).strip():
                            self.stdout.write("  - Điều kiện để tạo Point: ĐẠT")
                            try:
                                # Chuyển đổi sang float một cách tường minh
                                lng_float = float(lng_val)
                                lat_float = float(lat_val)

                                self.stdout.write(f"  - Đã chuyển đổi thành công: lng={lng_float}, lat={lat_float}")

                                point_obj = Point(lng_float, lat_float, srid=4326)
                                self.stdout.write(f"  - Đã tạo đối tượng Point: {point_obj.wkt}")

                            except (ValueError, TypeError) as e:
                                self.stdout.write(
                                    self.style.ERROR(f"  - LỖI khi chuyển đổi tọa độ hoặc tạo Point: {e}"))
                                point_obj = None
                        else:
                            self.stdout.write("  - Điều kiện để tạo Point: KHÔNG ĐẠT (giá trị rỗng hoặc None)")

                        location_obj = Location.objects.create(
                            street=source_data.get('street', ''), ward=ward_obj,
                            point=point_obj
                        )
                        # In ra giá trị point ngay sau khi lưu để xác nhận
                        self.stdout.write(f"  - Giá trị Point đã lưu vào CSDL: {location_obj.point}")
                        # ==========================================================
                        # <<< KHỐI DEBUG KẾT THÚC >>>
                        # ==========================================================

                        property_obj = Property.objects.create(id=source_property_id, owner=user,
                                                               property_type=property_type_motel, location=location_obj,
                                                               area=float(source_data.get('area', 0)))
                        price_val, unit_price_obj = parse_price(source_data.get('price'), source_data.get('unit_price'))
                        Listing.objects.create(
                            property=property_obj, user=user, listing_type=listing_type_rent,
                            title=source_data.get('title', 'N/A')[:255], content=source_data.get('description', ''),
                            price_value=price_val, unit_price=unit_price_obj,
                            created_date=source_data.get('created_at', datetime.now()),
                        )

                        migrated_count += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Lỗi nghiêm trọng khi xử lý tin {source_property_id}: {e}"))
                    skipped_count += 1

        self.stdout.write(self.style.SUCCESS("\n--- HOÀN TẤT QUÁ TRÌNH ---"))
        self.stdout.write(f"Tổng số tin đã di chuyển: {migrated_count}")
        self.stdout.write(f"Tổng số tin bị bỏ qua/lỗi: {skipped_count}")