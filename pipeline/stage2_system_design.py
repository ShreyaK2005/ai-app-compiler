import json
from utils.llm_client import LLMClient
from config.schemas import UserIntent, SystemDesign
from validation.schema_validator import SchemaValidator
from config.constants import STAGE_PROMPTS
from utils.logger import log_info, log_error, log_stage


class SystemDesigner:
    """Stage 2: Convert intent to system design"""

    def __init__(self):
        self.llm = LLMClient()
        self.validator = SchemaValidator()

    def design(self, intent: UserIntent) -> tuple[bool, SystemDesign, dict]:
        """
        Convert intent to system design.

        Returns:
            (success, design_object, metadata)
        """
        log_stage("stage_2", "system_design")

        try:
            # Convert intent to JSON for prompt
            intent_json = intent.model_dump_json(indent=2)

            # Call LLM with system design prompt
            prompt = STAGE_PROMPTS["system_design"].format(intent_json=intent_json)

            log_info("Calling LLM for system design...")
            response = self.llm.call_llm(prompt)

            # Parse JSON response
            design_dict = json.loads(response)

            # Validate against schema
            is_valid, design, errors = self.validator.validate_design(design_dict)

            if not is_valid:
                log_error(f"Design validation failed: {errors}")
                return False, None, {
                    "status": "failed",
                    "errors": errors,
                    "raw_output": response
                }

            log_info(f"System design created: {design.app_name}")

            return True, design, {
                "status": "success",
                "app_name": design.app_name,
                "entities_count": len(design.entities),
                "roles_count": len(design.roles),
                "flows_count": len(design.flows)
            }

        except json.JSONDecodeError as e:
            log_error(f"JSON parse error in system design: {str(e)}")
            return False, None, {
                "status": "failed",
                "error": "JSON_PARSE_ERROR",
                "message": str(e)
            }

        except Exception as e:
            log_error(f"System design failed: {str(e)}")
            return False, None, {
                "status": "failed",
                "error": str(type(e).__name__),
                "message": str(e)
            }
