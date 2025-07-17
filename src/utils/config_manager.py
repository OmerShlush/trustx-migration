import os
import json
from typing import Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)

class ConfigManager:
    """Manages configuration loading from environment variables and config files."""

    def __init__(self, config_file_path: str = "config/config.json"):
        self.config_file_path = config_file_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        config = self._load_from_file()
        config = self._override_with_env_vars(config)
        return config

    def _load_from_file(self) -> Dict[str, Any]:
        try:
            if not os.path.exists(self.config_file_path):
                logger.error(f"Configuration file not found: {self.config_file_path}")
                logger.info("Please copy config/config.template.json to config/config.json and update the values")
                raise FileNotFoundError(f"Configuration file not found: {self.config_file_path}")

            with open(self.config_file_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Configuration loaded from {self.config_file_path}")
                return config
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise

    def _override_with_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Override configuration values with environment variables."""
        env_mappings = {
            # Source
            'TRUSTX_SOURCE_BASE_URL': ('source', 'base_url'),
            'TRUSTX_SOURCE_PROCESS_DEFINITION_ID': ('source', 'process_definition_id'),
            'TRUSTX_SOURCE_API_KEY': ('source', 'api_key'),

            # Destination
            'TRUSTX_DEST_BASE_URL': ('dest', 'base_url'),
            'TRUSTX_DEST_API_KEY': ('dest', 'api_key'),
            'TRUSTX_DEST_PROCESS_DEFINITION_NAME': ('dest', 'process_definition_name'),

            # General
            'TRUSTX_OUTPUT_DIR': ('output_dir',),

            # Logging
            'TRUSTX_LOG_FILE': ('logging', 'log_file'),
            'TRUSTX_LOG_LEVEL_CONSOLE': ('logging', 'log_level_console'),
            'TRUSTX_LOG_LEVEL_FILE': ('logging', 'log_level_file'),
            'TRUSTX_LOG_MAX_BYTES': ('logging', 'max_bytes'),
            'TRUSTX_LOG_BACKUP_COUNT': ('logging', 'backup_count')
        }

        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Handle numeric types for logging config
                if config_path[0] == 'logging' and config_path[1] in ('max_bytes', 'backup_count'):
                    try:
                        env_value = int(env_value)
                    except ValueError:
                        logger.warning(f"Invalid numeric value for {env_var}: {env_value}, skipping override.")
                        continue
                self._set_nested_value(config, config_path, env_value)
                logger.debug(f"Overriding config with environment variable {env_var}")

        return config

    def _set_nested_value(self, config: Dict[str, Any], path: tuple, value: Any):
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def get_source_config(self) -> Dict[str, str]:
        return self.config.get('source', {})

    def get_dest_config(self) -> Dict[str, str]:
        return self.config.get('dest', {})

    def get_logging_config(self) -> Dict[str, Any]:
        return self.config.get('logging', {})

    def validate_config(self) -> bool:
        required_fields = [
            ('source', 'base_url'),
            ('source', 'process_definition_id'),
            ('source', 'api_key'),
            ('dest', 'base_url'),
            ('dest', 'api_key'),
            ('dest', 'process_definition_name'),
        ]

        missing_fields = []
        for section, field in required_fields:
            if not self.get(f"{section}.{field}"):
                missing_fields.append(f"{section}.{field}")

        if missing_fields:
            logger.error(f"Missing required configuration fields: {', '.join(missing_fields)}")
            return False

        logger.info("Configuration validation passed")
        return True
