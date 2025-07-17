# TrustX Migration Tool

A comprehensive migration tool for TrustX process definitions, including BPMN files, cloud functions, custom data forms, custom pages, and themes.

## Features

- **Process Definition Migration**: Migrate complete process definitions between TrustX environments
- **Asset Management**: Automatically handle cloud functions, custom data forms, custom pages, and themes
- **BPMN Processing**: Extract and update BPMN references during migration
- **Configuration Management**: Flexible configuration via JSON files and environment variables
- **Comprehensive Logging**: Detailed logging for troubleshooting and audit trails
- **Error Handling**: Robust error handling with graceful degradation

## Prerequisites

- Python 3.8 or higher
- TrustX API access (API keys for source and destination environments)
- Network access to TrustX environments

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd TrustX-Migration
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up configuration**:
   ```bash
   cp config/config.template.json config/config.json
   ```

4. **Edit the configuration file** (`config/config.json`) with your environment details:
   ```json
   {
       "source": {
           "base_url": "https://your-source-environment.trustx.com",
           "process_definition_id": "YOUR_SOURCE_PROCESS_DEFINITION_ID",
           "api_key": "YOUR_SOURCE_API_KEY"
       },
       "dest": {
           "base_url": "https://your-destination-environment.trustx.com",
           "api_key": "YOUR_DESTINATION_API_KEY",
           "process_definition_name": "YOUR_NEW_PROCESS_DEFINITION_NAME"
       },
       "output_dir": "output",
        "logging": {
            "log_file": "logs/migration.log",
            "log_level_console": "INFO",
            "log_level_file": "DEBUG",
            "max_bytes": 5000000,
            "backup_count": 5
        }
   }
   ```

## Configuration

### Configuration File

The tool uses a JSON configuration file located at `config/config.json`. You can use the template file `config/config.template.json` as a starting point.

### Environment Variables

You can override configuration values using environment variables:

| Environment Variable | Description | Config Path |
|---------------------|-------------|-------------|
| `TRUSTX_SOURCE_BASE_URL` | Source environment URL | `source.base_url` |
| `TRUSTX_SOURCE_PROCESS_DEFINITION_ID` | Source process definition ID | `source.process_definition_id` |
| `TRUSTX_SOURCE_API_KEY` | Source environment API key | `source.api_key` |
| `TRUSTX_DEST_BASE_URL` | Destination environment URL | `dest.base_url` |
| `TRUSTX_DEST_API_KEY` | Destination environment API key | `dest.api_key` |
| `TRUSTX_DEST_PROCESS_DEFINITION_NAME` | New process definition name | `dest.process_definition_name` |
| `TRUSTX_OUTPUT_DIR` | Output directory | `output_dir` |
| `TRUSTX_LOG_LEVEL` | Logging level | `logging.level` |
| `TRUSTX_LOG_FILE` | Log file path | `logging.file` |
| `TRUSTX_CREATED_BY` | Creator email for migration | `migration.created_by` |
| `TRUSTX_TENANT_ID` | Tenant ID for migration | `migration.tenant_id` |

### Example Environment Setup

```bash
export TRUSTX_SOURCE_BASE_URL="https://dev.trustx.com"
export TRUSTX_SOURCE_API_KEY="your-dev-api-key"
export TRUSTX_DEST_BASE_URL="https://prod.trustx.com"
export TRUSTX_DEST_API_KEY="your-prod-api-key"
export TRUSTX_SOURCE_PROCESS_DEFINITION_ID="ABC123DEF456"
export TRUSTX_DEST_PROCESS_DEFINITION_NAME="Production_Process_v2"
```

## Usage

### Basic Migration

Run the migration tool:

```bash
python src/main.py
```

### Migration Process

The tool performs the following steps:

1. **Configuration Validation**: Validates all required configuration parameters
2. **Authentication**: Obtains bearer tokens for both environments
3. **BPMN Extraction**: Fetches and saves the source BPMN file
4. **Asset Discovery**: Extracts references to cloud functions, custom forms, and custom pages
5. **Asset Migration**: 
   - Downloads cloud functions and saves as Python files
   - Downloads custom data forms and saves as JSON
   - Downloads custom pages with assets
   - Downloads and migrates themes
6. **Asset Deployment**: 
   - Creates cloud functions in destination environment
   - Creates custom data forms in destination environment
   - Creates custom pages in destination environment
   - Pushes themes to destination environment
7. **BPMN Update**: Updates BPMN file with new asset versions
8. **Process Definition Creation**: Creates the new process definition in destination

### Output Structure

After migration, the `output` directory will contain:

```
output/
├── {process_definition_id}.bpmn          # Original BPMN file
├── {process_definition_name}.bpmn        # Updated BPMN file
├── data/
│   ├── cf/                               # Cloud function files
│   ├── forms/                            # Custom data form files
│   ├── custom_pages/                     # Custom page files
│   └── theme/                            # Theme files
└── results/
    ├── aggregation.json                  # Migration summary
    ├── {cloud_function_name}.json        # Cloud function creation results
    ├── {form_name}.json                  # Form creation results
    ├── {page_name}.json                  # Page creation results
    └── theme.json                        # Theme creation results
```

## Project Structure

```
TrustX Migration/
├── config/
│   ├── config.json                       # Configuration file (not in git)
│   └── config.template.json              # Configuration template
├── logs/
│   └── migration.log                     # Migration logs
├── output/                               # Migration output (not in git)
├── src/
│   ├── auth/
│   │   └── token_manager.py              # Authentication management
│   ├── core/
│   │   └── migration_engine.py           # Main migration logic
│   ├── services/
│   │   ├── bpmn_manager.py               # BPMN file handling
│   │   ├── cf_manager.py                 # Cloud function management
│   │   ├── cdf_manager.py                # Custom data form management
│   │   ├── cp_manager.py                 # Custom page management
│   │   ├── pd_manager.py                 # Process definition management
│   │   └── theme_manager.py              # Theme management
│   ├── utils/
│   │   ├── config_manager.py             # Configuration management
│   │   └── logger.py                     # Logging utilities
│   └── main.py                           # Application entry point
├── requirements.txt                      # Python dependencies
├── README.md                             # This file
└── .gitignore                            # Git ignore rules
```

## Error Handling

The tool includes comprehensive error handling:

- **Configuration Errors**: Validates configuration before starting migration
- **Network Errors**: Handles API timeouts and connection issues
- **Asset Migration Errors**: Continues migration even if individual assets fail
- **Logging**: All errors are logged with detailed information

### Common Issues

1. **API Key Issues**: Ensure API keys are valid and have appropriate permissions
2. **Network Connectivity**: Verify network access to TrustX environments
3. **Asset Dependencies**: Some assets may have dependencies that need to be created manually
4. **Watchlists**: Watchlists must be created manually in the destination environment

## Logging

The tool provides detailed logging at multiple levels:

- **INFO**: General migration progress
- **DEBUG**: Detailed API calls and processing steps
- **WARNING**: Non-critical issues that don't stop migration
- **ERROR**: Critical issues that may affect migration

Logs are written to both console and file (configurable in `config.json`).

## Security Considerations

- **API Keys**: Never commit API keys to version control
- **Configuration**: Use environment variables for sensitive data
- **Network**: Ensure secure network connections to TrustX environments
- **Output**: Migration output may contain sensitive data

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Support

For support and questions:

- Create an issue in the repository
- Contact the development team
- Check the logs for detailed error information

## Changelog

### Version 1.0.0
- Initial release
- Support for process definition migration
- Asset management (cloud functions, forms, pages, themes)
- Configuration management with environment variable support
- Comprehensive logging and error handling