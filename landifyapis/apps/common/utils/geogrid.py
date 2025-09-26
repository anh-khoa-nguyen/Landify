# apps/common/utils/geogrid.py
import math

# Kích thước của mỗi ô lưới (tính bằng độ vĩ tuyến/kinh tuyến)
# 0.01 độ ~ 1.11km.
GRID_SIZE_DEGREES = 0.01


class GeoGridConverter:
    def __init__(self, grid_size=GRID_SIZE_DEGREES):
        self.grid_size = grid_size
        self.precision = int(abs(math.log10(grid_size)))

    def get_cell_id(self, lat: float, lng: float) -> str:
        """Chuyển đổi tọa độ (lat, lng) thành một ID ô lưới duy nhất."""
        if lat is None or lng is None:
            return None

        # Làm tròn tọa độ xuống theo kích thước ô lưới
        cell_lat = math.floor(lat / self.grid_size) * self.grid_size
        cell_lng = math.floor(lng / self.grid_size) * self.grid_size

        # Tạo ID dạng chuỗi
        return f"cell_{cell_lat:.{self.precision}f}_{cell_lng:.{self.precision}f}"

    def get_cell_center(self, cell_id: str) -> tuple | None:
        """Lấy tọa độ trung tâm của một ô lưới từ ID của nó."""
        try:
            parts = cell_id.split('_')
            lat = float(parts[1])
            lng = float(parts[2])

            center_lat = lat + self.grid_size / 2
            center_lng = lng + self.grid_size / 2
            return (center_lat, center_lng)
        except (IndexError, ValueError):
            return None


# Tạo một instance để sử dụng trong toàn bộ dự án
geogrid_converter = GeoGridConverter()