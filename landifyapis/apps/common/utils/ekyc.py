from typing import Any, Dict

import requests
from django.conf import settings

def call_fpt_idr_api(id_card_image_file) -> Dict[str, Any]:
    """Gọi API FPT ID Recognition để trích xuất thông tin từ ảnh CCCD."""
    url = "https://api.fpt.ai/vision/idr/vnm"
    headers = {"api-key": settings.FPT_AI_API_KEY}
    files = {"image": id_card_image_file.read()}
    response = requests.post(url, files=files, headers=headers)
    response.raise_for_status()
    return response.json()


def call_fpt_liveness_api(video_file, id_card_image_data) -> Dict[str, Any]:
    """Gọi API FPT Liveness để xác thực người thật và so khớp khuôn mặt."""
    url = "https://api.fpt.ai/dmp/liveness/v3"
    headers = {"api-key": settings.FPT_AI_API_KEY}
    files = {
        "video": ("video.mp4", video_file.read(), "application/octet-stream"),
        "cmnd": ("id_card.jpg", id_card_image_data, "application/octet-stream"),
    }
    response = requests.post(url, headers=headers, files=files)
    response.raise_for_status()
    return response.json()
