import json
import os
from pathlib import Path

import django
import google.auth
import requests
from google.auth.transport.requests import Request

# Import BASE_DIR và CONFIG_FILES_MAP từ settings
from landifyapis.settings import BASE_DIR

print("INFO: Initializing Django environment...")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "landifyapis.settings")
django.setup()
print("INFO: Django environment setup complete.")

CONFIG_DATA_DIR = BASE_DIR / "config_data"
SCOPES = ["https://www.googleapis.com/auth/firebase.remoteconfig"]

CONFIG_FILES_MAP = {
    "home_property_types": "home_property_types.json",
    "home_features": "home_features.json",
}


def _get_access_token_and_project_id():
    # Kiểm tra GOOGLE_APPLICATION_CREDENTIALS được set từ settings
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not set")
    credentials, project_id = google.auth.default(scopes=SCOPES)
    credentials.refresh(Request())
    return credentials.token, project_id


def _read_config_from_json(filename):
    filepath = CONFIG_DATA_DIR / filename
    print(f"-> Reading config from '{filepath}'...")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        print(f"   ...Success, found {len(data)} items.")
        return data


def run():
    print("\nStarting Firebase Remote Config synchronization...")
    token, project_id = _get_access_token_and_project_id()
    url = f"https://firebaseremoteconfig.googleapis.com/v1/projects/{project_id}/remoteConfig"
    headers = {"Authorization": f"Bearer {token}"}

    print("Fetching existing template...")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    template = response.json()
    etag = response.headers["ETag"]
    print(f"Successfully fetched template (ETag: {etag}).")

    print("\nProcessing local configuration files:")
    for param_key, filename in CONFIG_FILES_MAP.items():
        data = _read_config_from_json(filename)
        if data:
            if "parameters" not in template:
                template["parameters"] = {}
            template["parameters"][param_key] = {
                "defaultValue": {"value": json.dumps(data, ensure_ascii=False)},
                "valueType": "STRING",
            }
            print(f"   ...Updated parameter '{param_key}'.")

    print("\nPublishing updated template to Firebase...")
    update_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; UTF-8",
        "If-Match": etag,
    }
    response = requests.put(url, headers=update_headers, json=template)
    response.raise_for_status()
    print("\n✅ SUCCESS: Published new Remote Config template.")
    print(f"New ETag: {response.headers['ETag']}")


if __name__ == "__main__":
    run()
