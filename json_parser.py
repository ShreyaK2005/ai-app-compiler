import json
import re
from typing import Optional, Dict, Any
from utils.logger import log_warning, log_error


def parse_json_safe(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Safely parse JSON from LLM response.

    Attempts:
    1. Direct parse
    2. Extract JSON from markdown code blocks
    3. Find JSON object with regex
    4. Repair common JSON errors
    """

    # Attempt 1: Direct parse
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: Extract from markdown code blocks
    code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
    if code_block_match:
        try:
            json_str = code_block_match.group(1)
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # Attempt 3: Find JSON object with regex
    # Look for { ... } pattern
    brace_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if brace_match:
        try:
            json_str = brace_match.group(0)
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # Attempt 4: Repair common JSON errors
    try:
        repaired = repair_json(response_text)
        return json.loads(repaired)
    except Exception as e:
        log_error(f"Could not repair JSON: {str(e)}")
        return None


def repair_json(json_str: str) -> str:
    """
    Repair common JSON formatting issues.
    """
    # Remove trailing commas before ] or }
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

    # Fix single quotes to double quotes (be careful with apostrophes)
    # Only do this for keys and simple string values
    json_str = re.sub(r"'([^']*)'(\s*:)", r'"\1"\2', json_str)

    # Add missing quotes around keys
    json_str = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3', json_str)

    # Fix common unicode/escape issues
    json_str = json_str.replace('\\', '\\\\').replace('\\"', '"')

    return json_str


def validate_json_structure(obj: Dict, required_keys: list) -> tuple[bool, list]:
    """
    Validate that JSON object has required keys.
    Returns (is_valid, missing_keys)
    """
    missing = [key for key in required_keys if key not in obj]
    return len(missing) == 0, missing


def extract_json_field(obj: Dict, field_path: str, default=None):
    """
    Extract nested field from JSON using dot notation.
    E.g., extract_json_field(obj, "entities.0.name")
    """
    keys = field_path.split('.')
    current = obj

    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        elif isinstance(current, list):
            try:
                current = current[int(key)]
            except (IndexError, ValueError):
                return default
        else:
            return default

    return current