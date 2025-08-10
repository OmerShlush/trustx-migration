import os
import base64
import requests
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

def fetch_bpmn(bearer_token: str, base_url: str, pd_id: str):
    url = f'{base_url}/api/process-manager/processDefinitions/{pd_id}'
    headers = {'Authorization': f'Bearer {bearer_token}', 'Accept': 'application/json, text/plain, */*'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        logger.info(f"{pd_id} has fetched.")
        return response.json().get("resources").get("bpmn").get("data")
    except Exception as e:
        logger.error(f"Failed to get token: {e}")
        raise

def save_bpmn(base64_data: str, filename: str = "onboarding_demo.bpmn", output_dir: str = "output"):
    try:
        bpmn_xml = base64.b64decode(base64_data)
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(bpmn_xml)
        logger.info(f"BPMN file saved to {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Failed to save BPMN file: {e}")
        raise

def extract_bpmn_references(xml_path: str) -> Dict[str, List[Dict]]:
    """
    Extracts references to cloud functions, custom forms, custom pages, and watchlists from BPMN XML.

    Returns:
    {
        "cloud_functions": [{"name": ..., "version": ...}],
        "custom_forms": [{"name": ..., "version": ...}],
        "custom_pages": [{"name": ..., "version": ..., "key": ...}],
        "watchlists": [{"name": ...}]
    }
    """
    def parse_version(text: Optional[str]) -> Optional[int]:
        if not text:
            return None
        text = text.strip()
        if text.startswith("${") and text.endswith("}"):
            text = text[2:-1]
        try:
            return int(text)
        except ValueError:
            return None

    tree = ET.parse(xml_path)
    root = tree.getroot()
    ns = {'camunda': 'http://camunda.org/schema/1.0/bpmn'}

    references = {
        "cloud_functions": [],
        "custom_forms": [],
        "custom_pages": [],
        "watchlists": []
    }

    for parent in root.findall(".//camunda:inputOutput", ns):
        block = {}
        for param in parent.findall("camunda:inputParameter", ns):
            name = param.attrib.get("name")
            text = param.text.strip() if param.text else ""
            block[name] = text

        if "functionName" in block:
            references["cloud_functions"].append({
                "name": block["functionName"],
                "version": parse_version(block.get("functionVersion"))
            })

        if "dataFormName" in block:
            references["custom_forms"].append({
                "name": block["dataFormName"],
                "version": parse_version(block.get("dataFormVersion"))
            })

        if "customPageName" in block:
            references["custom_pages"].append({
                "name": block["customPageName"],
                "version": parse_version(block.get("customPageVersion")),
                "key": block.get("customPageKey")
            })

        if "watchlistName" in block:
            references["watchlists"].append({
                "name": block["watchlistName"]
            })

    return references



from lxml import etree
import os
from typing import Dict, List

from utils.logger import get_logger

logger = get_logger(__name__)

def update_bpmn_versions(
    bpmn_path: str,
    aggregation: Dict[str, List[Dict]],
    output_dir: str,
    pd_name: str
) -> str:
    """
    Safely updates only version fields in BPMN file using lxml to preserve namespace prefixes.
    """
    try:
        parser = etree.XMLParser(remove_blank_text=False)
        tree = etree.parse(bpmn_path, parser)
        root = tree.getroot()

        nsmap = root.nsmap
        camunda_ns = nsmap.get("camunda") or "http://camunda.org/schema/1.0/bpmn"

        cf_versions = {cf["name"]: cf.get("version") for cf in aggregation.get("cloud_functions", [])}
        form_versions = {f["name"]: f.get("version") for f in aggregation.get("custom_forms", [])}
        page_versions = {p["name"]: p.get("version") for p in aggregation.get("custom_pages", [])}

        logger.info("Using lxml to update BPMN version fields safely...")

        for io in root.xpath(".//camunda:inputOutput", namespaces=nsmap):
            input_params = io.xpath("camunda:inputParameter", namespaces=nsmap)
            param_map = {p.get("name"): p for p in input_params if p.get("name")}

            # Cloud Function
            if "functionName" in param_map and "functionVersion" in param_map:
                name = param_map["functionName"].text.strip()
                if name in cf_versions:
                    old = param_map["functionVersion"].text
                    param_map["functionVersion"].text = str(cf_versions[name])
                    logger.debug(f"Updated CF version for '{name}': {old} -> {cf_versions[name]}")

            # Custom Form
            if "dataFormName" in param_map and "dataFormVersion" in param_map:
                name = param_map["dataFormName"].text.strip()
                if name in form_versions:
                    old = param_map["dataFormVersion"].text
                    param_map["dataFormVersion"].text = str(form_versions[name])
                    logger.debug(f"Updated Form version for '{name}': {old} -> {form_versions[name]}")

            # Custom Page
            if "customPageName" in param_map and "customPageVersion" in param_map:
                name = param_map["customPageName"].text.strip()
                if name in page_versions:
                    old = param_map["customPageVersion"].text
                    param_map["customPageVersion"].text = str(page_versions[name])
                    logger.debug(f"Updated Page version for '{name}': {old} -> {page_versions[name]}")

        # Save updated BPMN
        output_path = os.path.join(output_dir, "data", f"{pd_name}.bpmn")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        tree.write(output_path, encoding="utf-8", xml_declaration=True, pretty_print=True)
        logger.info(f"Updated BPMN saved to: {output_path}")

        return output_path

    except Exception as e:
        logger.error(f"Failed to update BPMN versions: {e}", exc_info=True)
        raise
