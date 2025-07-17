from utils.logger import get_logger
from utils.config_manager import ConfigManager
from core.migration_engine import MigrationEngine

logger = get_logger(__name__)

def main():
    logger.info("TrustX Migration Started")
    
    # Load and validate configuration
    config_manager = ConfigManager()
    if not config_manager.validate_config():
        logger.error("Configuration validation failed. Please check your config file and environment variables.")
        return
    
    config = config_manager.config
    engine = MigrationEngine(config)

    engine.migrate_process_definition(
        api_key=config["source"]["api_key"],
        source_base_url=config["source"]["base_url"],
        dest_base_url=config["dest"]["base_url"],
        pd_id=config["source"]["process_definition_id"],
        pd_name=config["dest"]["process_definition_name"],
        output_dir=config.get("output_dir", "output")
    )

if __name__ == "__main__":
    main()
