import json
import re
from utils.llm_client import LLMClient
from config.schemas import UserIntent
from validation.schema_validator import SchemaValidator
from config.constants import STAGE_PROMPTS
from utils.logger import log_info, log_error, log_stage, log_debug
from utils.json_parser import parse_json_safe


class IntentExtractor:
    """Stage 1: Extract structured intent from raw user prompt"""

    def __init__(self):
        self.llm = LLMClient()
        self.validator = SchemaValidator()

    def extract(self, user_prompt: str) -> tuple:
        """
        Extract user intent from natural language prompt.

        Returns:
            (success, intent_object, metadata)
        """
        log_stage("stage_1", "intent_extraction")

        try:
            # Call LLM with intent extraction prompt
            prompt = STAGE_PROMPTS["intent_extraction"].format(prompt=user_prompt)

            log_info("Calling LLM for intent extraction...")
            response = self.llm.call_llm(prompt)
            intent_dict = parse_json_safe(response)

            if intent_dict is None:
                log_error("Failed to parse JSON from LLM response")
                return False, None, {
                    "status": "failed",
                    "error": "JSON_PARSE_ERROR",
                    "message": "Could not extract valid JSON from response",
                    "raw_response": response[:500]
                }

            is_valid, intent, errors = self.validator.validate_intent(intent_dict)

            if not is_valid:
                log_error(f"Intent validation failed: {errors}")
                return False, None, {
                    "status": "failed",
                    "errors": errors,
                    "raw_output": response[:500]
                }

            log_info(f"Intent extracted successfully: {intent.app_type}")

            return True, intent, {
                "status": "success",
                "app_type": intent.app_type,
                "features_count": len(intent.core_features),
                "roles_count": len(intent.user_roles)
            }


        except Exception as e:
            log_error(f"Intent extraction failed: {str(e)}")
            import traceback
            log_debug(traceback.format_exc())
            return False, None, {
                "status": "failed",
                "error": str(type(e).__name__),
                "message": str(e)
            }

    def _parse_json_response(self, response: str):
        """Parse JSON from LLM response with multiple fallback strategies."""
        if not response or not isinstance(response, str):
            return None

        response = response.strip()

        # Strategy 1: Direct parse
        try:
            return json.loads(response)
        except:
            pass

        # Strategy 2: Extract from markdown code block
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass

        # Strategy 3: Find JSON object by braces
        start = response.find('{')
        end = response.rfind('}')

        if start != -1 and end != -1 and end > start:
            try:
                json_str = response[start:end + 1]
                return json.loads(json_str)
            except:
                pass

        # Strategy 4: Extract complete JSON object
        if '{' in response:
            try:
                json_str = self._extract_complete_json(response)
                if json_str:
                    return json.loads(json_str)
            except:
                pass

        # Strategy 5: Repair and parse
        try:
            repaired = self._repair_json_string(response)
            if repaired:
                return json.loads(repaired)
        except:
            pass

        log_debug(f"Could not parse JSON from response: {response[:300]}")
        return None

    def _extract_complete_json(self, text: str):
        """Extract a complete JSON object from text"""
        start = text.find('{')
        if start == -1:
            return None

        brace_count = 0
        in_string = False
        escape = False

        for i in range(start, len(text)):
            char = text[i]

            if escape:
                escape = False
                continue

            if char == '\\':
                escape = True
                continue

            if char == '"':
                in_string = not in_string
                continue

            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return text[start:i + 1]

        return text[start:] if brace_count > 0 else None

    def _repair_json_string(self, text: str) -> str:
        """Repair common JSON formatting issues"""

        # Remove trailing commas
        text = re.sub(r',(\s*[}\]])', r'\1', text)

        # Add quotes around unquoted keys
        text = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3', text)

        # Fix single quotes to double quotes (for keys)
        text = re.sub(r"'([^']*)'(\s*:)", r'"\1"\2', text)

        return text

