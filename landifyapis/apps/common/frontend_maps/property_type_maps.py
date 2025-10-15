# D:\Backend\Landify\landifyapis\apps\common\frontend_maps\property_type_maps.py

PROPERTY_TYPE_MAP = {
    "APARTMENT": {"icon_code": "building"},
    "TOWNHOUSE": {"icon_code": "house"},
    "LAND": {"icon_code": "mountainSun"},
    "OFFICE": {"icon_code": "store"},
    "VILLA": {"icon_code": "houseFlag"},
    "MOTEL_ROOM": {"icon_code": "personShelter"},
    "WAREHOUSE": {"icon_code": "warehouse"},
}

DEFAULT_PROPERTY_TYPE_INFO = {"icon_code": "buildingUser"}


def get_property_type_frontend_info(code: str) -> dict:
    return PROPERTY_TYPE_MAP.get(code, DEFAULT_PROPERTY_TYPE_INFO)
