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
        """Load configuration from file and environment variables."""
        config = self._load_from_file()
        config = self._override_with_env_vars(config)
        return config
    
    def _load_from_file(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
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
            # Source environment
            'TRUSTX_SOURCE_BASE_URL': ('source', 'base_url'),
            'TRUSTX_SOURCE_PROCESS_DEFINITION_ID': ('source', 'process_definition_id'),
            'TRUSTX_SOURCE_API_KEY': ('source', 'api_key'),
            
            # Destination environment
            'TRUSTX_DEST_BASE_URL': ('dest', 'base_url'),
            'TRUSTX_DEST_API_KEY': ('dest', 'api_key'),
            'TRUSTX_DEST_PROCESS_DEFINITION_NAME': ('dest', 'process_definition_name'),
            
            # General settings
            'TRUSTX_OUTPUT_DIR': ('output_dir',),
            'TRUSTX_LOG_LEVEL': ('logging', 'level'),
            'TRUSTX_LOG_FILE': ('logging', 'file'),
            
            # Migration settings
            'TRUSTX_CREATED_BY': ('migration', 'created_by'),
            'TRUSTX_TENANT_ID': ('migration', 'tenant_id'),
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                self._set_nested_value(config, config_path, env_value)
                logger.debug(f"Overriding config with environment variable {env_var}")
        
        return config
    
    def _set_nested_value(self, config: Dict[str, Any], path: tuple, value: str):
        """Set a nested value in the configuration dictionary."""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation."""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_source_config(self) -> Dict[str, str]:
        """Get source environment configuration."""
        return self.config.get('source', {})
    
    def get_dest_config(self) -> Dict[str, str]:
        """Get destination environment configuration."""
        return self.config.get('dest', {})
    
    def get_migration_config(self) -> Dict[str, str]:
        """Get migration-specific configuration."""
        return self.config.get('migration', {})
    
    def get_logging_config(self) -> Dict[str, str]:
        """Get logging configuration."""
        return self.config.get('logging', {})
    
    def validate_config(self) -> bool:
        """Validate that all required configuration values are present."""
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