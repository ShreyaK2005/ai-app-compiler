import time
import json
from utils.logger import log_info, log_error, log_stage, log_debug
from utils.llm_client import LLMClient
from pipeline.stage1_intent_extraction import IntentExtractor
from pipeline.stage2_system_design import SystemDesigner
from pipeline.stage3_schema_generation import SchemaGenerator
from pipeline.stage4_refinement import Refiner
from config.schemas import AppConfig


class PipelineCoordinator:
    """
    Orchestrates the entire 4-stage pipeline:
    1. Intent Extraction
    2. System Design
    3. Schema Generation
    4. Refinement
    """

    def __init__(self):
        self.intent_extractor = IntentExtractor()
        self.system_designer = SystemDesigner()
        self.schema_generator = SchemaGenerator()
        self.refiner = Refiner()
        self.llm = LLMClient()

    def process(self, user_prompt: str) -> tuple[bool, AppConfig, dict]:
        """
        Process user prompt through entire pipeline.

        Returns:
            (success, app_config, execution_details)
        """
        log_stage("pipeline", "starting")

        start_time = time.time()
        execution_details = {
            "original_prompt": user_prompt,
            "stages": {}
        }

        # Compute prompt hash for consistency tracking
        prompt_hash = self.llm.compute_prompt_hash(user_prompt)
        log_debug(f"Prompt hash: {prompt_hash}")

        # ===== STAGE 1: INTENT EXTRACTION =====
        log_info("=" * 60)
        log_info("STAGE 1: INTENT EXTRACTION")
        log_info("=" * 60)

        success, intent, metadata = self.intent_extractor.extract(user_prompt)
        execution_details["stages"]["intent_extraction"] = metadata

        if not success:
            log_error("Stage 1 failed")
            return False, None, {
                **execution_details,
                "failed_at_stage": 1,
                "error": metadata
            }

        log_info(f"✓ Stage 1 complete. Intent: {intent.app_type}")

        # ===== STAGE 2: SYSTEM DESIGN =====
        log_info("=" * 60)
        log_info("STAGE 2: SYSTEM DESIGN")
        log_info("=" * 60)

        success, design, metadata = self.system_designer.design(intent)
        execution_details["stages"]["system_design"] = metadata

        if not success:
            log_error("Stage 2 failed")
            return False, None, {
                **execution_details,
                "failed_at_stage": 2,
                "error": metadata
            }

        log_info(f"✓ Stage 2 complete. App: {design.app_name}")

        # ===== STAGE 3: SCHEMA GENERATION =====
        log_info("=" * 60)
        log_info("STAGE 3: SCHEMA GENERATION")
        log_info("=" * 60)

        success, schemas, metadata = self.schema_generator.generate(design)
        execution_details["stages"]["schema_generation"] = metadata

        if not success:
            log_error("Stage 3 failed")
            return False, None, {
                **execution_details,
                "failed_at_stage": 3,
                "error": metadata
            }

        log_info(f"✓ Stage 3 complete. {metadata['api_endpoints']} endpoints, {metadata['db_tables']} tables")

        # ===== STAGE 4: REFINEMENT =====
        log_info("=" * 60)
        log_info("STAGE 4: REFINEMENT & VALIDATION")
        log_info("=" * 60)

        success, app_config, metadata = self.refiner.refine(
            schemas["ui_schema"],
            schemas["api_schema"],
            schemas["db_schema"],
            schemas["auth_rules"],
            prompt_hash
        )
        execution_details["stages"]["refinement"] = metadata

        if not success:
            log_error("Stage 4 failed")
            return False, None, {
                **execution_details,
                "failed_at_stage": 4,
                "error": metadata
            }

        log_info(f"✓ Stage 4 complete. App ID: {app_config.app_id}")

        # ===== PIPELINE COMPLETE =====
        elapsed = time.time() - start_time

        log_stage("pipeline", "complete")
        log_info(f"✓✓✓ PIPELINE COMPLETE in {elapsed:.2f}s ✓✓✓")

        execution_details.update({
            "success": True,
            "elapsed_seconds": elapsed,
            "app_id": app_config.app_id,
            "app_name": app_config.app_name
        })

        return True, app_config, execution_details

    def get_output_json(self, app_config: AppConfig) -> str:
        """Convert AppConfig to JSON for output"""
        return app_config.model_dump_json(indent=2)