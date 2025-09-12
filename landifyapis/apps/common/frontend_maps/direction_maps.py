# D:\Backend\Landify\landifyapis\apps\common\frontend_maps\direction_maps.py

DIRECTION_MAP = {
    "EAST": {"icon_code": "e"},
    "WEST": {"icon_code": "w"},
    "SOUTH": {"icon_code": "s"},
    "NORTH": {"icon_code": "n"},
    "SOUTHEAST": {"icon_code": "arrowUpRightDots"}, # Ví dụ, cần icon phù hợp
    "NORTHWEST": {"icon_code": "arrowUpLeftDots"},
    "NORTHEAST": {"icon_code": "arrowDownLeftDots"},
    "SOUTHWEST": {"icon_code": "arrowDownRightDots"},
}

DEFAULT_DIRECTION_INFO = {"icon_code": "compass"}

def get_direction_frontend_info(code: str) -> dict:
    return DIRECTION_MAP.get(code, DEFAULT_DIRECTION_INFO)