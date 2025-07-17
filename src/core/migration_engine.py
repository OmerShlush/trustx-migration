from utils.logger import get_logger
from auth.token_manager import get_token
from services.bpmn_manager import fetch_bpmn, save_bpmn, extract_bpmn_references, update_bpmn_versions
from services.cf_manager import get_cloud_function_details, save_cloud_function_to_file, create_cloud_function
from services.cdf_manager import get_custom_data_form_details, save_custom_data_form_to_file, create_custom_data_form
from services.cp_manager import get_custom_page_details, create_custom_page
from services.theme_manager import fetch_theme_id, fetch_and_save_theme, push_theme_to_env
from services.pd_manager import create_process_definition
import os
import shutil
import json


logger = get_logger(__name__)

def _clean_output_folder(folder_path: str = "output"):
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    os.makedirs(folder_path, exist_ok=True)
    logger.info(f"Cleaned output folder: {folder_path}")

class MigrationEngine:
    def __init__(self, config: dict):
        self.config = config
        logger.info("Migration engine initialized.")

    def migrate_process_definition(self, api_key: str, dest_api_key: str, source_base_url: str, dest_base_url: str, pd_id: str, pd_name: str, output_dir: str = "output"):
        _clean_output_folder(output_dir)
        logger.info(f"Starting migration for process definition: {pd_id}")
        try:
            logger.debug("Obtaining a bearer tokens...")
            token = get_token(api_key, source_base_url)
            dest_token = get_token(dest_api_key, dest_base_url)

            logger.debug("Fetching BPMN data...")
            bpmn_data = fetch_bpmn(token, source_base_url, pd_id)
            
            bpmn_filename = f"{pd_id}.bpmn"
            logger.debug("Saving BPMN to file...")
            save_bpmn(bpmn_data, filename=bpmn_filename, output_dir=output_dir)
        
            bpmn_path = os.path.join("output", bpmn_filename)
            logger.debug("Extracting BPMN references (CFs, CDFs, Pages)...")
            assets = extract_bpmn_references(bpmn_path)

            logger.info(f"Found BPMN Assets: {assets}")

            watchlists = assets.get("watchlists", [])
            if watchlists:
                watchlist_names = [w["name"] for w in watchlists]
                logger.warning("Watchlists must be created manually in the destination environment before proceeding.")
                logger.warning(f"Watchlists detected: {watchlist_names}")
                input("Press [Enter] to confirm watchlists exist and continue migration...")

            for cf in assets.get("cloud_functions", []):
                try:
                    logger.info(f"Fetching Cloud Function: {cf['name']} (v{cf.get('version')})")
                    cf_data = get_cloud_function_details(source_base_url, cf["name"], token, cf.get("version"))
                    save_cloud_function_to_file(cf["name"], cf_data, output_dir=f'{output_dir}/data/cf')
                except Exception as e:
                    logger.warning(f"Failed to migrate Cloud Function '{cf['name']}': {e}")

            for form in assets.get("custom_forms", []):
                try:
                    logger.info(f"Fetching Custom Form: {form['name']} (v{form.get('version')})")
                    form_data = get_custom_data_form_details(source_base_url, form["name"], token, form.get("version"))
                    save_custom_data_form_to_file(form["name"], form_data, output_dir=f'{output_dir}/data/forms')
                except Exception as e:
                    logger.warning(f"Failed to migrate Custom Form '{form['name']}': {e}")

            for page in assets.get("custom_pages", []):
                try:
                    logger.info(f"Fetching Custom Page: {page['name']} (v{page.get('version')})")
                    get_custom_page_details(
                        base_url=source_base_url,
                        page_name=page["name"],
                        access_token=token,
                        version=page.get("version"),
                        download_assets=True,
                        output_dir=f'{output_dir}/data/custom_pages'
                    )
                except Exception as e:
                    logger.warning(f"Failed to migrate Custom Page '{page['name']}': {e}")

            aggregation = {
                "theme": None,
                "cloud_functions": [],
                "custom_forms": [],
                "custom_pages": [],
                "watchlists": watchlists
            }


            theme_id = fetch_theme_id(token, source_base_url, pd_id)
            if theme_id is not None:
                theme_path = fetch_and_save_theme(token, theme_id, source_base_url, output_dir=f'{output_dir}/data/theme')

                created_theme = push_theme_to_env(
                    bearer_token=dest_token,
                    base_url=dest_base_url,
                    theme_json_path=f"{theme_path}/theme.json",
                    assets_folder=f"{theme_path}/assets"
                )

                aggregation["theme"] = created_theme


            for cf in assets.get("cloud_functions", []):
                try:
                    logger.info(f"Pushing Cloud Function: {cf['name']} (v{cf.get('version')})")
                    cf_script_path = os.path.join(output_dir, "data", "cf", f"{cf['name']}.py")
                    with open(cf_script_path, "r") as script_file:
                        SCRIPT = script_file.read()
                    created_cf_result = create_cloud_function(dest_base_url, dest_token, cf["name"], SCRIPT, output_file=f'{output_dir}/results/{cf["name"]}.json')
                    aggregation["cloud_functions"].append(created_cf_result)
                except Exception as e:
                    logger.warning(f"Failed to push Cloud Function '{cf['name']}': {e}")

            for form in assets.get("custom_forms", []):
                try:
                    logger.info(f"Pushing Custom Form: {form['name']} (v{form.get('version')})")
                    form_script_path = os.path.join(output_dir, "data", "forms", f"{form['name']}.json")
                    with open(form_script_path, "r") as script_file:
                        SCRIPT = script_file.read()
                    created_form_result = create_custom_data_form(dest_base_url, dest_token, form["name"], SCRIPT, output_file=f'{output_dir}/results/{form["name"]}.json')
                    aggregation["custom_forms"].append(created_form_result)
                except Exception as e:
                    logger.warning(f"Failed to push Custom Form '{form['name']}': {e}")

            for page in assets.get("custom_pages", []):
                try:
                    logger.info(f"Pushing Custom Page: {page['name']} (v{page.get('version')})")
                    zip_path = os.path.join(f'{output_dir}/data/custom_pages/', f'{page['name']}_v{page.get('version', 1)}.zip')
                    created_cp_result = create_custom_page(dest_base_url, dest_token, page["name"], zip_path, output_file=f'{output_dir}/results/{page["name"]}.json')
                    aggregation["custom_pages"].append(created_cp_result)
                except Exception as e:
                    logger.warning(f"Failed to migrate Custom Page '{page['name']}': {e}")

            # Save aggregated data to file
            agg_path = os.path.join(output_dir, "results", "aggregation.json")
            os.makedirs(os.path.dirname(agg_path), exist_ok=True)

            with open(agg_path, "w") as agg_file:
                json.dump(aggregation, agg_file, indent=2)
                logger.info(f"Migration aggregation saved to {agg_path}")

            # Update BPMN File
            updated_bpmn_path = update_bpmn_versions(
                bpmn_path=os.path.join(output_dir, f"{pd_id}.bpmn"),
                aggregation=aggregation,
                output_dir=output_dir,
                pd_name=pd_name
            )

            # Create Process Definition
            create_process_definition(
            dest_base_url,
            dest_token,
            name=pd_name,
            bpmn_file_path=updated_bpmn_path,
            theme_id=theme_id
            )
        except Exception as e:
            logger.error(f"Error migrating process definition {pd_id}: {str(e)}", exc_info=True)
