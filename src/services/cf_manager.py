import os
import requests
import json
from typing import Optional, Dict, Any, Union, List
from utils.logger import get_logger

logger = get_logger(__name__)


def _get_headers(access_token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }


def _get_function_versions(base_url: str, function_name: str, headers: Dict[str, str]) -> List[dict]:
    versions = []
    page = 0
    size = 20
    found_version_1 = False

    while True:
        params = {
            "page": page,
            "size": size,
            "sort": "version,desc"
        }
        url = f"{base_url}/api/process-manager/cloudFunctions/{function_name}/versions"
        logger.debug(f"Fetching versions for {function_name}, page {page}")
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        page_data = response.json()
        content = page_data.get("content", [])
        if not content:
            break

        versions.extend(content)

        # Stop if version 1 is found
        if any(v.get("version") == 1 for v in content):
            found_version_1 = True
            break

        if page_data.get("last", True):
            break

        page += 1

    if not found_version_1:
        logger.warning(f"Version 1 not found for function {function_name} after checking all pages.")

    return versions

def _select_function_version(versions: list, version: Optional[int], function_name: str) -> Dict[str, Any]:
    if version is not None:
        match = next((v for v in versions if v["version"] == version), None)
        if not match:
            raise ValueError(f"Version {version} not found for cloud function '{function_name}'")
        return match
    else:
        match = next((v for v in versions if v["status"] == "DEPLOYED_ACTIVE"), None)
        if not match:
            raise ValueError(f"No active (DEPLOYED_ACTIVE) version found for cloud function '{function_name}'")
        return match


def _get_function_detail(base_url: str, function_id: str, headers: Dict[str, str]) -> Union[str, dict]:
    url = f"{base_url}/api/process-manager/cloudFunctions/{function_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    resource = response.json().get("resource")

    if not resource:
        raise ValueError("Missing 'resource' in cloud function detail response")

    return resource


def get_cloud_function_details(
    base_url: str,
    function_name: str,
    access_token: str,
    version: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetch cloud function details by specific version or latest active version.
    Always returns a dict with a 'script' key.
    """
    try:
        headers = _get_headers(access_token)
        versions = _get_function_versions(base_url, function_name, headers)

        if not versions:
            raise ValueError(f"No versions found for cloud function '{function_name}'")

        selected = _select_function_version(versions, version, function_name)
        resource = _get_function_detail(base_url, selected["id"], headers)

        if isinstance(resource, str):
            return {"script": resource}
        elif isinstance(resource, dict):
            return resource
        else:
            raise TypeError("Unexpected 'resource' type in response")

    except requests.RequestException as req_err:
        logger.error(f"Request failed while fetching cloud function '{function_name}': {req_err}")
        raise
    except Exception as err:
        logger.error(f"Unexpected error for cloud function '{function_name}': {err}")
        raise


def save_cloud_function_to_file(function_name: str, resource: Union[str, dict], output_dir: str = "output/data/cf") -> None:
    """
    Saves cloud function content to a .py file.
    Supports raw script strings or structured dicts containing a 'script' key.
    """
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{function_name}.py")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            if isinstance(resource, str):
                f.write(resource.strip())
            elif isinstance(resource, dict) and "script" in resource:
                f.write(resource["script"].strip())
            else:
                f.write("# Auto-generated cloud function (unexpected structure)\n")
                f.write(f"{function_name}_details = {repr(resource)}\n")

        logger.info(f"Saved cloud function to: {file_path}")

    except Exception as e:
        logger.error(f"Failed to save cloud function '{function_name}' to file: {e}")
        raise
def create_cloud_function(
    base_url: str,
    access_token: str,
    function_name: str,
    script: str,
    cf_type: str = "PYTHON39V1",
    description: str = "",
    output_file: str = "output/data/created_cf_info.json"
) -> Dict[str, Any]:
    """
    Creates a cloud function and activates it. Returns the full metadata response.
    """
    headers = _get_headers(access_token)
    create_url = f"{base_url}/api/process-manager/cloudFunctions"

    payload = {
        "name": function_name,
        "description": description,
        "status": "EDITABLE",
        "type": cf_type,
        "resource": script
    }

    try:
        logger.info(f"Creating cloud function '{function_name}'...")
        response = requests.post(create_url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        function_id = result["id"]
        logger.info(f"Cloud function created: {function_id}")

        # Activate it
        return activate_cloud_function(
            base_url,
            access_token,
            result,
            output_file
        )

    except Exception as e:
        logger.error(f"Failed to create cloud function '{function_name}': {e}", exc_info=True)
        raise


def activate_cloud_function(
    base_url: str,
    access_token: str,
    metadata: Dict[str, Any],
    output_file: str = "output/data/created_cf_info.json"
) -> Dict[str, Any]:
    """
    Activates a cloud function using its metadata.
    Saves the final result and returns it.
    """
    headers = _get_headers(access_token)
    function_id = metadata["id"]
    function_name = metadata["name"]
    activate_url = f"{base_url}/api/process-manager/cloudFunctions/{function_id}/status/DEPLOYED_ACTIVE"

    activation_payload = {}

    try:
        logger.info(f"Activating cloud function '{function_name}'...")
        response = requests.post(activate_url, headers=headers, json=activation_payload)
        response.raise_for_status()
        final_info = response.json()

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_info, f, indent=2)
        logger.info(f"Cloud function activated and saved: {output_file}")

        return final_info

    except Exception as e:
        logger.error(f"Failed to activate cloud function '{function_name}': {e}", exc_info=True)
        raise
