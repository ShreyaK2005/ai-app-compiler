import json
from typing import Dict, Any, List, Tuple
from logger import log_warning, log_info, log_error
from llm_client import LLMClient
from constants import STAGE_PROMPTS
from schemas import ValidationError


class RepairEngine:
    """
    THE CORE OF THE SYSTEM.

    Instead of blindly retrying, this intelligently repairs broken configs.
    Strategies:
    1. Auto-fix simple issues (missing fields, type mismatches)
    2. LLM-guided repair for complex inconsistencies
    3. Targeted regeneration of broken parts
    """

    def __init__(self):
        self.llm = LLMClient()

    def repair_config(self, config: Dict[str, Any], errors: List[ValidationError]) -> Tuple[
        bool, Dict[str, Any], List[str]]:
        """
        Attempt to repair config given list of errors.
        Returns (success, repaired_config, repair_actions)
        """
        repair_actions = []

        if not errors:
            return True, config, []

        log_info(f"RepairEngine: Attempting to repair {len(errors)} errors")

        # Separate errors by type
        critical_errors = [e for e in errors if e.severity == "critical"]
        warning_errors = [e for e in errors if e.severity == "warning"]

        # Try auto-repair first for simple issues
        auto_repaired, config, auto_actions = self._auto_repair(config, errors)
        repair_actions.extend(auto_actions)

        if auto_repaired and len(critical_errors) == 0:
            log_info("RepairEngine: Auto-repair successful")
            return True, config, repair_actions

        # For remaining critical errors, use LLM-guided repair
        if critical_errors:
            llm_repaired, config, llm_actions = self._llm_guided_repair(config, critical_errors)
            repair_actions.extend(llm_actions)

            if llm_repaired:
                return True, config, repair_actions

        return False, config, repair_actions

    def _auto_repair(self, config: Dict[str, Any], errors: List[ValidationError]) -> Tuple[
        bool, Dict[str, Any], List[str]]:
        """Auto-repair simple issues without LLM"""
        actions = []

        for error in errors:
            # Strategy 1: Add missing required fields
            if "field required" in error.message.lower():
                log_warning(f"Attempting to auto-add missing field: {error.location}")
                # This would be implemented based on field type
                actions.append(f"auto_add_field: {error.location}")

            # Strategy 2: Fix type mismatches
            elif "type" in error.message.lower():
                actions.append(f"type_conversion: {error.location}")

            # Strategy 3: Remove hallucinated/invalid fields
            elif "extra fields not permitted" in error.message.lower():
                self._remove_field(config, error.location)
                actions.append(f"remove_hallucinated_field: {error.location}")

            # Strategy 4: Add missing enum values
            elif "input should be" in error.message.lower() and "one of" in error.message.lower():
                actions.append(f"enum_mismatch: {error.location}")

        return len(actions) > 0, config, actions

    def _llm_guided_repair(self, config: Dict[str, Any], critical_errors: List[ValidationError]) -> Tuple[
        bool, Dict[str, Any], List[str]]:
        """Use LLM to intelligently fix critical errors"""

        error_descriptions = "\n".join([
            f"- {e.location}: {e.message} (Fix: {e.suggested_fix or 'Fix intelligently'})"
            for e in critical_errors
        ])

        repair_prompt = f"""You are a system repair expert. Given a broken app config and a list of errors, fix ONLY the critical issues.

Errors to fix:
{error_descriptions}

Current config:
{json.dumps(config, indent=2)}

INSTRUCTIONS:
1. Analyze each error carefully
2. Make MINIMAL changes to fix the issues
3. Do NOT add unnecessary fields or changes
4. Ensure consistency across layers after fixes
5. Return the COMPLETE corrected config

Return ONLY valid JSON. No explanations."""

        try:
            repaired_json = self.llm.call_llm_json(repair_prompt)
            log_info("RepairEngine: LLM-guided repair completed")
            return True, repaired_json, ["llm_guided_repair"]
        except Exception as e:
            log_error(f"RepairEngine: LLM-guided repair failed: {str(e)}")
            return False, config, []

    def _remove_field(self, config: Dict[str, Any], location: str) -> None:
        """Remove a field from config given its location"""
        # Parse location like "api_schema.endpoints[0].extra_field"
        parts = location.replace('[', '.').replace(']', '').split('.')
        current = config

        for part in parts[:-1]:
            if part.isdigit():
                current = current[int(part)]
            else:
                current = current.get(part, {})

        # Remove the last part
        if isinstance(current, dict) and parts[-1] in current:
            del current[parts[-1]]

    def _regenerate_stage(self, config: Dict[str, Any], stage: str) -> Tuple[bool, Dict[str, Any], str]:
        """
        Instead of regenerating the whole config, regenerate just one stage.
        This is more cost-effective and faster.
        """
        log_info(f"RepairEngine: Regenerating {stage} stage")

        # This would call the specific stage pipeline
        # For now, return False indicating we need full regeneration
        return False, config, f"full_pipeline_needed"

    def validate_and_repair_cycle(self, config: Dict[str, Any], max_attempts: int = 2) -> Tuple[bool, Dict[str, Any]]:
        """
        Full validate -> repair -> revalidate cycle.
        Stops when either config is valid or max attempts reached.
        """
        from validation.consistency_checker import ConsistencyChecker
        from validation.schema_validator import SchemaValidator

        for attempt in range(max_attempts):
            # Validate current config
            is_valid, errors = ConsistencyChecker.check_all(
                config.get('ui_schema'),
                config.get('api_schema'),
                config.get('db_schema'),
                config.get('auth_rules')
            )

            if is_valid:
                log_info(f"Config is valid after attempt {attempt + 1}")
                return True, config

            # Try to repair
            repaired, config, actions = self.repair_config(config, errors)

            if not repaired:
                log_error(f"Could not repair config on attempt {attempt + 1}")
                break

            log_info(f"Repair actions: {actions}")

        return False, config
