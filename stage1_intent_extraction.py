import json
from llm_client import LLMClient
from schemas import UserIntent
from schema_validator import SchemaValidator
from constants import STAGE_PROMPTS
from logger import log_info, log_error, log_stage


class IntentExtractor:
    """Stage 1: Extract structured intent from raw user prompt"""

    def __init__(self):
        self.llm = LLMClient()
        self.validator = SchemaValidator()

    def extract(self, user_prompt: str) -> tuple[bool, UserIntent, dict]:
        """
        Extract user intent from natural language prompt.

        Returns:
            (success, intent_object, metadata)
        """
        log_stage("stage_1", "intent_extraction")

        try:
            # Call LLM with intent extraction prompt
            prompt = STAGE_PROMPTS["intent_extraction"].replace(
                "{prompt}",
                user_prompt
            )

            print("Prompt formatted successfully")

            print("\n========== GENERATED PROMPT ==========")
            print(prompt[:500])
            print("=====================================\n")

            log_info("Calling LLM for intent extraction...")
            response = self.llm.call_llm(prompt)

            # Parse JSON response
            intent_dict = json.loads(response)

            # Validate against schema
            is_valid, intent, errors = self.validator.validate_intent(intent_dict)

            if not is_valid:
                log_error(f"Intent validation failed: {errors}")
                return False, None, {
                    "status": "failed",
                    "errors": errors,
                    "raw_output": response
                }

            log_info(f"Intent extracted successfully: {intent.app_type}")

            return True, intent, {
                "status": "success",
                "app_type": intent.app_type,
                "features_count": len(intent.core_features),
                "roles_count": len(intent.user_roles)
            }

        except json.JSONDecodeError as e:
            log_error(f"JSON parse error in intent extraction: {str(e)}")
            return False, None, {
                "status": "failed",
                "error": "JSON_PARSE_ERROR",
                "message": str(e)
            }

        except Exception as e:
            log_error(f"Intent extraction failed: {str(e)}")
            return False, None, {
                "status": "failed",
                "error": str(type(e).__name__),
                "message": str(e)
            }

