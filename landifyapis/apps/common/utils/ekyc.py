import json
from typing import Any, Dict

import requests
from django.conf import settings


def call_cccd_ocr_api(id_card_image_file) -> Dict[str, Any]:
    """Gọi microservices OCR CCCD tự xây dựng để trích xuất thông tin từ ảnh CCCD."""
    url = "https://dorangao-landify-cccd-ocr.hf.space/extract/"
    headers = {}
    files = {"file": id_card_image_file.read()}
    response = requests.post(url, files=files, headers=headers)
    response.raise_for_status()
    return response.json()


def call_liveness_verification_api(video_file, ocr_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gọi microservice Liveness Verification tự xây dựng.
    API này nhận vào file video và một chuỗi JSON chứa dữ liệu từ bước OCR.
    """
    url = "https://dorangao-landify-liveless-verification.hf.space/verify/"
    headers = {}

    json_data_str = json.dumps(ocr_data)

    files = {"video_file": video_file.read(), "json_data": (None, json_data_str, "application/json")}
    response = requests.post(url, files=files, headers=headers)
    response.raise_for_status()
    return response.json()
