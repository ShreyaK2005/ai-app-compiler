import json
import re
from typing import Optional, Dict, Any
from utils.logger import log_warning, log_error, log_debug


def parse_json_safe(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Safely parse JSON from LLM response.
    Handles various formats that LLMs might return.
    """

    if not response_text or not isinstance(response_text, str):
        log_error(f"Invalid response type: {type(response_text)}")
        return None

    # Clean up the response
    response_text = response_text.strip()

    # Attempt 1: Direct parse (most common)
    try:
        result = json.loads(response_text)
        log_debug("JSON parsed directly")
        return result
    except json.JSONDecodeError as e:
        log_debug(f"Direct parse failed: {str(e)[:100]}")

    # Attempt 2: Extract from markdown code blocks
    code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
    if code_block_match:
        try:
            json_str = code_block_match.group(1).strip()
            result = json.loads(json_str)
            log_debug("JSON extracted from code block")
            return result
        except json.JSONDecodeError as e:
            log_debug(f"Code block parse failed: {str(e)[:100]}")

    # Attempt 3: Find JSON object with regex
    # Look for { ... } pattern, handling nested braces
    brace_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', response_text, re.DOTALL)
    if brace_match:
        try:
            json_str = brace_match.group(0)
            result = json.loads(json_str)
            log_debug("JSON extracted via regex")
            return result
        except json.JSONDecodeError as e:
            log_debug(f"Regex extract failed: {str(e)[:100]}")

    # Attempt 4: Find JSON array
    array_match = re.search(r'\[(?:[^\[\]]|(?:\[[^\[\]]*\]))*\]', response_text, re.DOTALL)
    if array_match:
        try:
            json_str = array_match.group(0)
            result = json.loads(json_str)
            log_debug("JSON array extracted via regex")
            return result
        except json.JSONDecodeError:
            pass

    # Attempt 5: Repair common JSON errors
    try:
        repaired = repair_json(response_text)
        if repaired:
            result = json.loads(repaired)
            log_debug("JSON repaired and parsed")
            return result
    except Exception as e:
        log_debug(f"Repair failed: {str(e)[:100]}")

    # Last attempt: Try to find key-value pairs and reconstruct
    try:
        reconstructed = reconstruct_json(response_text)
        if reconstructed:
            result = json.loads(reconstructed)
            log_debug("JSON reconstructed from key-value pairs")
            return result
    except Exception as e:
        log_error(f"All JSON parsing attempts failed: {str(e)[:100]}")

    return None


def repair_json(json_str: str) -> str:
    """Repair common JSON formatting issues."""

    # Remove BOM if present
    if json_str.startswith('\ufeff'):
        json_str = json_str[1:]

    # Remove trailing commas before ] or }
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

    # Fix single quotes to double quotes (carefully)
    # Only for simple cases like 'key':
    json_str = re.sub(r"'([^']*)'(\s*:)", r'"\1"\2', json_str)

    # Add missing quotes around keys
    # Match: {key: value or ,key: value
    json_str = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3', json_str)

    # Fix common escape issues
    # Handle line breaks in JSON
    json_str = json_str.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')

    # Fix unquoted values that should be quoted (strings with spaces)
    # This is tricky, so we'll be conservative

    return json_str


def reconstruct_json(text: str) -> Optional[str]:
    """Try to reconstruct JSON from text with key-value pairs."""

    # Look for patterns like: "key": "value" or "key": value
    pattern = r'"([^"]+)"\s*:\s*([^,}]*(?:\{[^}]*\})?[^,}]*)'
    matches = re.findall(pattern, text)

    if not matches or len(matches) < 2:
        return None

    # Build a JSON object from matches
    obj = {}
    for key, value in matches:
        value = value.strip()

        # Try to parse value as JSON
        try:
            obj[key] = json.loads(value)
        except:
            # If it fails, treat as string
            if value.lower() in ('true', 'false', 'null'):
                obj[key] = json.loads(value.lower())
            elif value.isdigit():
                obj[key] = int(value)
            else:
                obj[key] = value

    if obj:
        return json.dumps(obj)

    return None


def validate_json_structure(obj: Dict, required_keys: list) -> tuple:
    """Validate that JSON object has required keys."""
    missing = [key for key in required_keys if key not in obj]
    return len(missing) == 0, missing


def extract_json_field(obj: Dict, field_path: str, default=None):
    """Extract nested field from JSON using dot notation."""
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
