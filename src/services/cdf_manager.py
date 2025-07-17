import os
import requests
import json
from typing import Optional, Union, Dict, Any, List
from utils.logger import get_logger

logger = get_logger(__name__)


def _get_headers(access_token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }


def _get_form_versions(base_url: str, form_name: str, headers: Dict[str, str]) -> List[dict]:
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
        url = f"{base_url}/api/process-manager/customDataForms/{form_name}/versions"
        logger.debug(f"Fetching versions for form {form_name}, page {page}")
        
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
        logger.warning(f"Version 1 not found for form {form_name} after checking all pages.")

    return versions


def _select_form_version(versions: list, version: Optional[int], form_name: str) -> Dict[str, Any]:
    if version is not None:
        selected = next((v for v in versions if v["version"] == version), None)
        if not selected:
            raise ValueError(f"Version {version} not found for custom data form '{form_name}'")
        return selected
    selected = next((v for v in versions if v["status"] == "DEPLOYED_ACTIVE"), None)
    if not selected:
        raise ValueError(f"No active (DEPLOYED_ACTIVE) version found for custom data form '{form_name}'")
    return selected


def _get_form_detail(base_url: str, form_id: str, headers: Dict[str, str]) -> Union[str, dict]:
    url = f"{base_url}/api/process-manager/customDataForms/{form_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    resource = response.json().get("resource")
    if not resource:
        raise ValueError("Missing 'resource' in custom data form detail response")
    return resource


def get_custom_data_form_details(
    base_url: str,
    form_name: str,
    access_token: str,
    version: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetch custom data form details by specific version or latest active version.
    Always returns a dict with a 'formDefinition' key.
    """
    try:
        headers = _get_headers(access_token)
        versions = _get_form_versions(base_url, form_name, headers)

        if not versions:
            raise ValueError(f"No versions found for custom data form '{form_name}'")

        selected = _select_form_version(versions, version, form_name)
        resource = _get_form_detail(base_url, selected["id"], headers)

        if isinstance(resource, str):
            return {"formDefinition": resource}
        elif isinstance(resource, dict):
            return resource
        else:
            raise TypeError("Unexpected 'resource' type in response")

    except requests.RequestException as req_err:
        logger.error(f"Request failed while fetching form '{form_name}': {req_err}")
        raise
    except Exception as err:
        logger.error(f"Unexpected error for custom data form '{form_name}': {err}")
        raise


def save_custom_data_form_to_file(
    form_name: str,
    resource: Union[str, Dict[str, Any]],
    output_dir: str = "output/data/forms"
) -> None:
    """
    Saves custom data form content as a .json file.
    Supports raw string or dict with 'formDefinition'.
    """
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{form_name}.json")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            if isinstance(resource, dict) and "formDefinition" in resource:
                f.write(resource["formDefinition"].strip())
            elif isinstance(resource, str):
                f.write(resource.strip())
            else:
                f.write("# Auto-generated custom form (unexpected structure)\n")
                f.write(repr(resource))
                f.write("\n")

        logger.info(f"Saved custom form to: {file_path}")

    except Exception as e:
        logger.error(f"Failed to save custom data form '{form_name}': {e}")
        raise

def create_custom_data_form(
    base_url: str,
    access_token: str,
    form_name: str,
    resource: str,
    description: str = "",
    output_file: str = "output/data/created_form_info.json"
) -> Dict[str, Any]:
    """
    Creates a custom data form with provided resource JSON.
    Automatically deploys it active and stores the final metadata.
    """
    headers = _get_headers(access_token)
    create_url = f"{base_url}/api/process-manager/customDataForms"

    payload = {
        "name": form_name,
        "description": description,
        "status": "EDITABLE",
        "resource": resource,
        "creationOption": "Save & Deploy"
    }

    try:
        logger.info(f"Creating custom data form '{form_name}'...")
        response = requests.post(create_url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        form_id = result["id"]
        logger.info(f"Form created with ID: {form_id}")

        # Activate the form
        return activate_custom_data_form(
            base_url,
            access_token,
            result,
            output_file
        )

    except Exception as e:
        logger.error(f"Failed to create custom data form '{form_name}': {e}", exc_info=True)
        raise


def activate_custom_data_form(
    base_url: str,
    access_token: str,
    metadata: Dict[str, Any],
    output_file: str = "output/data/created_form_info.json"
) -> Dict[str, Any]:
    """
    Activates a custom data form using its metadata.
    """
    headers = _get_headers(access_token)
    form_id = metadata["id"]
    form_name = metadata["name"]
    activate_url = f"{base_url}/api/process-manager/customDataForms/{form_id}/status/DEPLOYED_ACTIVE"

    activation_payload = {}

    try:
        logger.info(f"Activating custom data form '{form_name}'...")
        response = requests.post(activate_url, headers=headers, json=activation_payload)
        response.raise_for_status()
        final_info = response.json()

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_info, f, indent=2)
        logger.info(f"Form activated and saved: {output_file}")

        return final_info

    except Exception as e:
        logger.error(f"Failed to activate custom data form '{form_name}': {e}", exc_info=True)
        raise

