import os
import json
import base64
import requests
from urllib.parse import urlparse
from utils.logger import get_logger

logger = get_logger(__name__)

def fetch_theme_id(bearer_token: str, base_url: str, pd_id: str):
    url = f'{base_url}/api/process-manager/processDefinitions/{pd_id}'
    headers = {'Authorization': f'Bearer {bearer_token}', 'Accept': 'application/json, text/plain, */*'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        logger.info(f"{pd_id} has fetched.")
        return response.json().get("themeId")
    except Exception as e:
        logger.error(f"Failed to get token: {e}")
        raise


def fetch_and_save_theme(bearer_token: str, theme_id: str, base_url: str, output_dir: str = "output/data/theme") -> str:
    url = f'{base_url}/api/theme-server/themes/{theme_id}/all'
    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'Accept': 'application/json'
    }

    try:
        logger.info(f"Fetching theme details for themeId: {theme_id}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        theme_data = response.json()

        theme_name = theme_data.get("name", "theme")
        version = theme_data.get("version", "v0")
        theme_folder = os.path.join(output_dir, f"{theme_name}_{theme_id}_v{version}")
        assets_folder = os.path.join(theme_folder, "assets")
        os.makedirs(assets_folder, exist_ok=True)

        json_path = os.path.join(theme_folder, "theme.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(theme_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Theme JSON saved to {json_path}")

        assets = theme_data.get("assets", {}).get("global", [])
        for asset in assets:
            asset_url = asset.get("path")
            if not asset_url:
                continue

            filename = os.path.basename(urlparse(asset_url).path)
            asset_path = os.path.join(assets_folder, filename)
            try:
                asset_response = requests.get(asset_url)
                asset_response.raise_for_status()
                with open(asset_path, "wb") as f:
                    f.write(asset_response.content)
                logger.info(f"Saved asset: {filename}")
            except Exception as e:
                logger.warning(f"Failed to download asset {asset_url}: {e}")
        return theme_folder
    except Exception as e:
        logger.error(f"Failed to fetch/save theme {theme_id}: {e}", exc_info=True)
        raise


def push_theme_to_env(bearer_token: str, base_url: str, theme_json_path: str, assets_folder: str,
                      output_file: str = "output/data/created_theme_info.json"):
    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    with open(theme_json_path, "r", encoding="utf-8") as f:
        theme_data = json.load(f)

    try:
        # Step 1: Create theme
        logger.info("Creating theme skeleton...")
        stripped_data = {
            "palette": theme_data["palette"],
            "status": "EDITABLE",
            "description": theme_data.get("description", ""),
            "name": theme_data["name"]
        }

        response = requests.post(f"{base_url}/api/theme-server/themes", headers=headers, json=stripped_data)
        logger.debug(response.json())
        response.raise_for_status()
        theme_id = response.json()["id"]
        logger.info(f"Theme created with ID: {theme_id}")

        # Step 2: Upload assets
        for filename in os.listdir(assets_folder):
            path = os.path.join(assets_folder, filename)
            with open(path, "rb") as f:
                content = base64.b64encode(f.read()).decode("utf-8")

            ext = filename.split(".")[-1]
            content_type = "font/ttf" if "font" in filename.lower() else f"image/{ext}"
            name = os.path.splitext(filename)[0]

            asset_payload = {
                "name": name,
                "contentType": content_type,
                "fileExtension": ext,
                "assetResource": content
            }

            try:
                asset_url = f"{base_url}/api/theme-server/themes/{theme_id}/assets/"
                asset_response = requests.post(asset_url, headers=headers, json=asset_payload)
                asset_response.raise_for_status()
                logger.info(f"Uploaded asset: {filename}")
            except Exception as e:
                logger.warning(f"Failed to upload {filename}: {e}")

        # Step 3: Update theme with full details
        logger.info("Updating theme with full JSON data...")
        update_url = f"{base_url}/api/theme-server/themes/{theme_id}"
        response = requests.post(update_url, headers=headers, json=theme_data)
        response.raise_for_status()

        # Step 4: Activate theme
        logger.info("Activating theme...")
        activation_url = f"{base_url}/api/theme-server/themes/{theme_id}/status/DEPLOYED_ACTIVE"
        payload = {}

        response = requests.post(activation_url, headers=headers, json=payload)
        response.raise_for_status()
        final_info = response.json()
        logger.info(f"Theme activated: {final_info}")

        # Step 5: Store final info
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_info, f, indent=2)
        logger.info(f"Final theme info stored at {output_file}")

        return final_info


    except Exception as e:
        logger.error(f"Failed to push theme: {e}", exc_info=True)
        raise
