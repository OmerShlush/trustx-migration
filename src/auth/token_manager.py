import requests
from utils.logger import get_logger

logger = get_logger(__name__)

def get_token(api_key: str, tenant_url: str) -> str:
    url = f"{tenant_url}/api/arthr/apiKeys/issue"
    headers = {"X-API-Key": api_key}
    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        return response.json().get("token")
    except Exception as e:
        logger.error(f"Failed to get token: {e}")
        raise
