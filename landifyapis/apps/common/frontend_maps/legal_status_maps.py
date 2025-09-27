# D:\Backend\Landify\landifyapis\apps\common\frontend_maps\legal_status_maps.py

LEGAL_STATUS_MAP = {
    "SOHONG": {"icon_code": "fileContract", "color_hex": "#FFC0CB"}, # Pink
    "SODO": {"icon_code": "fileSignature", "color_hex": "#FF6347"}, # Red
    "HDMB": {"icon_code": "fileInvoice", "color_hex": "#ADD8E6"}, # Light Blue
    "OTHER": {"icon_code": "fileQuestion", "color_hex": "#D3D3D3"}, # Light Grey
}

DEFAULT_LEGAL_STATUS_INFO = {"icon_code": "file", "color_hex": "#808080"}

def get_legal_status_frontend_info(code: str) -> dict:
    return LEGAL_STATUS_MAP.get(code, DEFAULT_LEGAL_STATUS_INFO)