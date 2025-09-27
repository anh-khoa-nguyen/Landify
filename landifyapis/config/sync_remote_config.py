# config/sync_remote_config.py
import os
import json
from pathlib import Path
import requests
import google.auth
from google.auth.transport.requests import Request

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'landifyapis.settings')
import django

django.setup()

# --- Các hằng số ---
CONFIG_DATA_DIR = Path(__file__).resolve().parent / "config_data"
CONFIG_FILES = {
    "home_property_types": "home_property_types.json",
    "home_features": "home_features.json",
}
SCOPES = ['https://www.googleapis.com/auth/firebase.remoteconfig']

try:
    # 1. Lấy Access Token và Project ID
    credentials, project_id = google.auth.default(scopes=SCOPES)
    credentials.refresh(Request())

    # 2. Lấy ETag của template hiện tại
    url = f'https://firebaseremoteconfig.googleapis.com/v1/projects/{project_id}/remoteConfig'
    headers = {'Authorization': f'Bearer {credentials.token}', 'Accept-Encoding': 'gzip'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    template = response.json()
    etag = response.headers['ETag']

    # 3. Đọc file và cập nhật template
    template['parameters'] = template.get('parameters', {})
    for param_key, filename in CONFIG_FILES.items():
        with open(CONFIG_DATA_DIR / filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            template['parameters'][param_key] = {
                'defaultValue': {'value': json.dumps(data, ensure_ascii=False)},
                'valueType': 'JSON'
            }

    # 4. Publish template mới
    update_headers = {**headers, 'Content-Type': 'application/json; charset=utf-8', 'If-Match': etag}
    response = requests.put(url, headers=update_headers, data=json.dumps(template).encode('utf-8'))
    response.raise_for_status()

    print(f"✅ Đồng bộ thành công! ETag mới: {response.headers['ETag']}")

except Exception as e:
    print(f"❌ LỖI: {e}")
    # In chi tiết lỗi nếu có phản hồi từ server
    if hasattr(e, 'response') and e.response is not None:
        print(f"   -> Chi tiết lỗi từ server: {e.response.text}")