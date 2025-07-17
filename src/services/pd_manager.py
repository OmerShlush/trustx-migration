import os
import json
import base64
import requests
from typing import Dict, Optional, Any
from utils.logger import get_logger

logger = get_logger(__name__)


def _get_headers(access_token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }


def _read_bpmn_file(bpmn_path: str) -> str:
    try:
        with open(bpmn_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
            logger.info(f"Encoded BPMN file: {bpmn_path}")
            return encoded
    except Exception as e:
        logger.error(f"Failed to read or encode BPMN file '{bpmn_path}': {e}", exc_info=True)
        raise


def create_process_definition(
    base_url: str,
    access_token: str,
    name: str,
    bpmn_file_path: str,
    server_type: str = "P1",
    process_definition_type: str = "VERIFICATION",
    description: str = "",
    theme_id: Optional[str] = None,
    output_file: str = "output/results/created_process_definition.json"
) -> Dict[str, Any]:
    try:
        headers = _get_headers(access_token)
        bpmn_encoded = _read_bpmn_file(bpmn_file_path)

        payload = {
            "name": name,
            "description": description,
            "serverType": server_type,
            "resources": {
                "bpmn": {
                    "data": bpmn_encoded,
                    "type": "BPMN"
                }
            },
            "processDefinitionType": process_definition_type,
            "attributes": {
                "searchable": True
            }
        }

        if theme_id:
            payload["themeId"] = theme_id

        url = f"{base_url}/api/process-manager/processDefinitions"
        logger.info(f"Creating process definition '{name}'...")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        logger.info(f"Process definition created: ID {result['id']}")

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        logger.info(f"Saved created process definition to {output_file}")
        activate_process_definition(
        base_url,
        access_token,
        result["id"],
        metadata=result
)
        return result

    except Exception as e:
        logger.error(f"Failed to create process definition '{name}': {e}", exc_info=True)
        raise


def activate_process_definition(
    base_url: str,
    access_token: str,
    process_definition_id: str,
    metadata: Dict[str, Any],
    output_file: str = "output/results/activated_process_definition.json"
) -> Dict[str, Any]:
    """
    Activates the given process definition using its ID and full metadata.
    """
    try:
        headers = _get_headers(access_token)
        url = f"{base_url}/api/process-manager/processDefinitions/{process_definition_id}/status/DEPLOYED_ACTIVE"

        logger.info(f"Activating process definition '{process_definition_id}'...")
        response = requests.post(url, headers=headers, json=metadata)
        response.raise_for_status()

        result = response.json()
        logger.info(f"Process definition activated successfully: ID {result['id']}")

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        logger.info(f"Saved activated process definition to {output_file}")

        return result

    except Exception as e:
        logger.error(f"Failed to activate process definition '{process_definition_id}': {e}", exc_info=True)
        raise
