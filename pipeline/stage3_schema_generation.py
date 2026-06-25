import json
from utils.llm_client import LLMClient
from config.schemas import SystemDesign, UISchema, APISchema, DBSchema, AuthRules
from validation.schema_validator import SchemaValidator
from config.constants import STAGE_PROMPTS
from utils.logger import log_info, log_error, log_stage


class SchemaGenerator:
    """Stage 3: Generate complete UI, API, DB, and Auth schemas"""

    def __init__(self):
        self.llm = LLMClient()
        self.validator = SchemaValidator()

    def generate(self, design: SystemDesign) -> tuple[bool, dict, dict]:
        """
        Generate all 4 schemas from system design.

        Returns:
            (success, {ui_schema, api_schema, db_schema, auth_rules}, metadata)
        """
        log_stage("stage_3", "schema_generation")

        try:
            # Convert design to JSON for prompt
            design_json = design.model_dump_json(indent=2)

            # Call LLM with schema generation prompt
            prompt = STAGE_PROMPTS["schema_generation"].format(design_json=design_json)



            # Parse JSON response
            from utils.json_parser import parse_json_safe

            log_info("Calling LLM for schema generation...")
            response = self.llm.call_llm(prompt)

            # DEBUG
            print("\n========== RAW SCHEMA OUTPUT ==========\n")
            print(response)
            print("\n=======================================\n")

            # Clean markdown/code fences
            response = response.strip()

            if response.startswith("```json"):
                response = response.replace("```json", "", 1)

            if response.startswith("```"):
                response = response.replace("```", "", 1)

            if response.endswith("```"):
                response = response[:-3]

            response = response.strip()

            # Remove any text after the final JSON object
            if "}" in response:
                response = response[:response.rfind("}") + 1]

            # Parse JSON response
            import re

            # Extract JSON from markdown/code block
            match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)

            if match:
                response = match.group(1)

            schemas_dict = json.loads(response)

            # Validate each schema
            ui_valid, ui_schema, ui_errors = self.validator.validate_ui_schema(schemas_dict.get("ui_schema", {}))
            api_valid, api_schema, api_errors = self.validator.validate_api_schema(schemas_dict.get("api_schema", {}))
            db_valid, db_schema, db_errors = self.validator.validate_db_schema(schemas_dict.get("db_schema", {}))
            auth_valid, auth_rules, auth_errors = self.validator.validate_auth_rules(schemas_dict.get("auth_rules", {}))

            all_valid = ui_valid and api_valid and db_valid and auth_valid
            all_errors = ui_errors + api_errors + db_errors + auth_errors

            if not all_valid:
                log_error(f"Schema validation failed: {all_errors}")
                return False, None, {
                    "status": "failed",
                    "errors": all_errors,
                    "raw_output": response
                }

            result = {
                "ui_schema": ui_schema,
                "api_schema": api_schema,
                "db_schema": db_schema,
                "auth_rules": auth_rules
            }

            log_info("All schemas generated successfully")

            return True, result, {
                "status": "success",
                "ui_pages": len(ui_schema.pages),
                "api_endpoints": len(api_schema.endpoints),
                "db_tables": len(db_schema.tables),
                "roles_defined": len(auth_rules.role_permissions)
            }

        except json.JSONDecodeError as e:
            log_error(f"JSON parse error in schema generation: {str(e)}")
            return False, None, {
                "status": "failed",
                "error": "JSON_PARSE_ERROR",
                "message": str(e)
            }

        except Exception as e:
            log_error(f"Schema generation failed: {str(e)}")
            return False, None, {
                "status": "failed",
                "error": str(type(e).__name__),
                "message": str(e)
            }
