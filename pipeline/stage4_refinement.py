import json
from typing import Dict, Any
from config.schemas import UISchema, APISchema, DBSchema, AuthRules, AppConfig
from validation.consistency_checker import ConsistencyChecker
from validation.repair_engine import RepairEngine
from utils.logger import log_info, log_error, log_stage, log_warning
import uuid
from datetime import datetime


class Refiner:
    """Stage 4: Refinement - Fix inconsistencies and validate"""

    def __init__(self):
        self.consistency_checker = ConsistencyChecker()
        self.repair_engine = RepairEngine()

    def refine(self, ui_schema: UISchema, api_schema: APISchema, db_schema: DBSchema, auth_rules: AuthRules,
               original_prompt_hash: str) -> tuple[bool, AppConfig, dict]:
        """
        Refine and validate all schemas together.
        Detect and fix inconsistencies.

        Returns:
            (success, app_config, metadata)
        """
        log_stage("stage_4", "refinement")

        try:
            # Check consistency across layers
            log_info("Checking cross-layer consistency...")
            is_consistent, errors = self.consistency_checker.check_all(
                ui_schema, api_schema, db_schema, auth_rules
            )

            if not is_consistent:
                log_warning(f"Found {len(errors)} consistency errors")
                for error in errors:
                    log_warning(f"  - {error.location}: {error.message}")

                # Attempt repairs
                log_info("Attempting auto-repair...")
                config_dict = {
                    "ui_schema": ui_schema.model_dump(),
                    "api_schema": api_schema.model_dump(),
                    "db_schema": db_schema.model_dump(),
                    "auth_rules": auth_rules.model_dump()
                }

                repaired, config_dict, repair_actions = self.repair_engine.repair_config(config_dict, errors)

                if not repaired:
                    log_error("Auto-repair failed")
                    return False, None, {
                        "status": "failed",
                        "reason": "repair_failed",
                        "errors": [{"location": e.location, "message": e.message} for e in errors]
                    }

                # Revalidate repaired config
                try:
                    ui_schema = UISchema(**config_dict["ui_schema"])
                    api_schema = APISchema(**config_dict["api_schema"])
                    db_schema = DBSchema(**config_dict["db_schema"])
                    auth_rules = AuthRules(**config_dict["auth_rules"])
                except Exception as e:
                    log_error(f"Repaired config failed validation: {str(e)}")
                    return False, None, {
                        "status": "failed",
                        "reason": "repair_validation_failed",
                        "error": str(e)
                    }

                log_info(f"Repair successful with {len(repair_actions)} actions")

            # Create final AppConfig
            app_id = str(uuid.uuid4())[:8]
            app_name = api_schema.endpoints[0].path.split('/')[1].upper() if api_schema.endpoints else "APP"

            app_config = AppConfig(
                app_id=app_id,
                app_name=app_name,
                version="1.0.0",
                description="Auto-generated application",
                ui_schema=ui_schema,
                api_schema=api_schema,
                db_schema=db_schema,
                auth_rules=auth_rules,
                created_at=datetime.now().isoformat(),
                prompt_hash=original_prompt_hash
            )

            log_info(f"Refinement complete. App ID: {app_id}")

            return True, app_config, {
                "status": "success",
                "app_id": app_id,
                "consistency_fixed": not is_consistent,
                "final_state": {
                    "ui_pages": len(ui_schema.pages),
                    "api_endpoints": len(api_schema.endpoints),
                    "db_tables": len(db_schema.tables),
                    "roles": len(auth_rules.role_permissions)
                }
            }

        except Exception as e:
            log_error(f"Refinement failed: {str(e)}")
            return False, None, {
                "status": "failed",
                "error": str(type(e).__name__),
                "message": str(e)
            }
