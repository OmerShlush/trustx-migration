import os
import zipfile
import base64
import requests
from urllib.parse import urljoin, urlparse
from typing import Optional, Dict, Any, List
from utils.logger import get_logger
from bs4 import BeautifulSoup 
import json

logger = get_logger(__name__)


def _get_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def _get_page_versions(base_url: str, name: str, headers: Dict[str, str]) -> List[dict]:
    versions = []
    page = 0
    size = 20  # Defaulting to 20 for consistency, even if API doesn't require it
    found_version_1 = False

    while True:
        params = {
            "page": page,
            "size": size,
            "sort": "version,desc"
        }
        url = f"{base_url}/api/theme-server/customPages/{name}/versions"
        logger.debug(f"Fetching versions for custom page '{name}', page {page}")

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        page_data = response.json()
        content = page_data.get("content", [])
        if not content:
            break

        versions.extend(content)

        if any(v.get("version") == 1 for v in content):
            found_version_1 = True
            break

        if page_data.get("last", True):
            break

        page += 1

    if not found_version_1:
        logger.warning(f"Version 1 not found for custom page '{name}' after checking all pages.")

    return versions



def _select_page_version(versions: list, version: Optional[int], name: str) -> Dict[str, Any]:
    if version is not None:
        selected = next((v for v in versions if v["version"] == version), None)
        if not selected:
            raise ValueError(f"Version {version} not found for custom page '{name}'")
        return selected

    selected = next((v for v in versions if v["status"] == "DEPLOYED_ACTIVE"), None)
    if not selected:
        raise ValueError(f"No active (DEPLOYED_ACTIVE) version found for custom page '{name}'")
    return selected


def _get_page_detail(base_url: str, page_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
    url = f"{base_url}/api/theme-server/customPages/{page_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def _zip_directory(source_dir: str, output_zip_path: str):
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=source_dir)
                zipf.write(file_path, arcname)
    logger.info(f"Created ZIP archive: {output_zip_path}")


def _download_preview_assets(preview_url: str, output_dir: str) -> None:
    try:
        os.makedirs(output_dir, exist_ok=True)
        resp = requests.get(preview_url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.content, "html.parser")
        index_path = os.path.join(output_dir, "index.html")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(str(soup))
        logger.info(f"Saved index.html to {index_path}")

        asset_links = set()
        for tag in soup.find_all("link", href=True):
            if tag.get("rel") and "stylesheet" in tag.get("rel"):
                asset_links.add(tag["href"].strip())
        for tag in soup.find_all("script", src=True):
            asset_links.add(tag["src"].strip())
        for tag in soup.find_all("img", src=True):
            asset_links.add(tag["src"].strip())

        base_url = os.path.dirname(preview_url.rstrip("/"))
        for asset_path in asset_links:
            if asset_path.startswith("data:") or asset_path.startswith("#"):
                continue

            asset_url = urljoin(base_url + "/", asset_path)
            try:
                asset_resp = requests.get(asset_url)
                asset_resp.raise_for_status()

                parsed_path = urlparse(asset_path).path
                rel_path = parsed_path.lstrip("/")
                local_asset_path = os.path.join(output_dir, rel_path)
                os.makedirs(os.path.dirname(local_asset_path), exist_ok=True)

                with open(local_asset_path, "wb") as f:
                    f.write(asset_resp.content)
                logger.info(f"Downloaded asset: {asset_url} → {local_asset_path}")
            except Exception as e:
                logger.warning(f"Failed to download asset '{asset_path}': {e}")

    except Exception as e:
        logger.error(f"Error downloading preview assets: {e}", exc_info=True)


def get_custom_page_details(
    base_url: str,
    page_name: str,
    access_token: str,
    version: Optional[int] = None,
    download_assets: bool = True,
    output_dir: str = "output/data/custom_pages"
) -> Dict[str, Any]:
    try:
        headers = _get_headers(access_token)
        versions = _get_page_versions(base_url, page_name, headers)
        if not versions:
            raise ValueError(f"No versions found for custom page '{page_name}'")

        selected = _select_page_version(versions, version, page_name)
        page_detail = _get_page_detail(base_url, selected["id"], headers)

        os.makedirs(output_dir, exist_ok=True)
        metadata_path = os.path.join(output_dir, f"{page_name}_v{selected['version']}.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(page_detail, f, indent=2)
        logger.info(f"Saved custom page metadata to: {metadata_path}")

        asset_dir = os.path.join(output_dir, page_name)
        if download_assets and "previewUrl" in page_detail:
            _download_preview_assets(page_detail["previewUrl"], output_dir=asset_dir)
            zip_path = os.path.join(output_dir, f"{page_name}_v{selected['version']}.zip")
            _zip_directory(asset_dir, zip_path)

        return page_detail

    except requests.RequestException as req_err:
        logger.error(f"Request failed for custom page '{page_name}': {req_err}")
        raise
    except Exception as err:
        logger.error(f"Unexpected error for custom page '{page_name}': {err}")
        raise


def create_custom_page(
    base_url: str,
    access_token: str,
    page_name: str,
    zip_path: str,
    description: str = "",
    output_file: str = "output/data/created_custom_page_info.json"
) -> Dict[str, Any]:
    headers = _get_headers(access_token)
    with open(zip_path, "rb") as f:
        encoded_archive = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "name": page_name,
        "description": description,
        "archive": encoded_archive,
        "creationOption": "Save & Deploy"
    }

    url = f"{base_url}/api/theme-server/customPages"
    try:
        logger.info(f"Uploading custom page '{page_name}'...")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Custom page created: ID {result['id']}")

        return activate_custom_page(
            base_url,
            access_token,
            result,
            output_file
        )
    except Exception as e:
        logger.error(f"Failed to upload custom page '{page_name}': {e}", exc_info=True)
        raise


def activate_custom_page(
    base_url: str,
    access_token: str,
    page_metadata: Dict[str, Any],
    output_file: str = "output/data/created_cf_info.json"
) -> Dict[str, Any]:
    headers = _get_headers(access_token)
    page_id = page_metadata["id"]
    activate_url = f"{base_url}/api/theme-server/customPages/{page_id}/status/DEPLOYED_ACTIVE"

    try:
        logger.info(f"Activating custom page '{page_metadata['name']}'...")
        response = requests.post(activate_url, headers=headers, json=page_metadata)
        response.raise_for_status()
        final_info = response.json()

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_info, f, indent=2)
        logger.info(f"Custom page activated and saved: {final_info['previewUrl']}")

        return final_info
    except Exception as e:
        logger.error(f"Failed to activate custom page '{page_metadata['name']}': {e}", exc_info=True)
        raise
