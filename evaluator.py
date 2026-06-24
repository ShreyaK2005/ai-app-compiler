import json
import time
from typing import List, Dict, Any
from constants import TEST_CASES
from schemas import EvaluationMetric, EvaluationReport
from coordinator import PipelineCoordinator
from runtime import Runtime
from logger import log_info, log_error
import statistics


class Evaluator:
    """Runs test cases and tracks metrics"""

    def __init__(self):
        self.coordinator = PipelineCoordinator()
        self.runtime = Runtime()
        self.metrics: List[EvaluationMetric] = []

    def run_all_tests(self) -> EvaluationReport:
        """Run all test cases and generate report"""
        log_info("=" * 60)
        log_info("STARTING EVALUATION RUN")
        log_info(f"Running {len(TEST_CASES)} test cases")
        log_info("=" * 60)

        self.metrics = []

        for test_case in TEST_CASES:
            self.run_single_test(test_case)

        return self._generate_report()

    def run_single_test(self, test_case: Dict[str, Any]):
        """Run a single test case and record metrics"""
        test_id = test_case["id"]
        test_type = test_case["type"]
        prompt = test_case["prompt"]

        log_info(f"\n{'=' * 60}")
        log_info(f"TEST: {test_id} ({test_type})")
        log_info(f"PROMPT: {prompt[:80]}...")
        log_info(f"{'=' * 60}")

        start_time = time.time()
        retries = 0
        success = False
        errors = []

        try:
            # Run pipeline
            success, app_config, details = self.coordinator.process(prompt)

            if success:
                # Validate with runtime
                runtime_success, runtime_errors, runtime_warnings = self.runtime.execute(app_config)
                success = runtime_success
                errors = runtime_errors
            else:
                errors = [details.get("error", "Unknown error")]

        except Exception as e:
            log_error(f"Test {test_id} crashed: {str(e)}")
            errors = [str(e)]
            success = False

        elapsed = time.time() - start_time

        # Record metric
        metric = EvaluationMetric(
            test_case_id=test_id,
            prompt=prompt,
            success=success,
            retries_needed=retries,
            time_taken_seconds=elapsed,
            validation_errors=errors,
            notes=f"Type: {test_type}"
        )

        self.metrics.append(metric)

        status = "✓ PASS" if success else "✗ FAIL"
        log_info(f"{status} - {elapsed:.2f}s - Errors: {len(errors)}")

    def _generate_report(self) -> EvaluationReport:
        """Generate evaluation report from metrics"""
        total = len(self.metrics)
        passed = sum(1 for m in self.metrics if m.success)
        failed = total - passed
        success_rate = (passed / total * 100) if total > 0 else 0

        retries = [m.retries_needed for m in self.metrics]
        avg_retries = statistics.mean(retries) if retries else 0

        times = [m.time_taken_seconds for m in self.metrics]
        avg_time = statistics.mean(times) if times else 0

        # Count failure types
        failure_types = {}
        for metric in self.metrics:
            if not metric.success:
                error_type = metric.validation_errors[0].split(':')[0] if metric.validation_errors else "unknown"
                failure_types[error_type] = failure_types.get(error_type, 0) + 1

        # Edge case performance
        edge_case_perf = {}
        for test_type in ["real", "edge_vague", "edge_conflicting", "edge_incomplete", "edge_ambiguous"]:
            type_metrics = [m for m in self.metrics if test_type in m.notes.lower()]
            if type_metrics:
                type_success = sum(1 for m in type_metrics if m.success)
                edge_case_perf[test_type] = (type_success / len(type_metrics) * 100) if type_metrics else 0

        report = EvaluationReport(
            total_tests=total,
            passed=passed,
            failed=failed,
            success_rate=success_rate,
            avg_retries=avg_retries,
            avg_time=avg_time,
            failure_types=failure_types,
            edge_case_performance=edge_case_perf
        )

        return report

    def print_report(self, report: EvaluationReport):
        """Pretty print evaluation report"""
        log_info("\n" + "=" * 60)
        log_info("EVALUATION REPORT")
        log_info("=" * 60)
        log_info(f"Total Tests:    {report.total_tests}")
        log_info(f"Passed:         {report.passed}")
        log_info(f"Failed:         {report.failed}")
        log_info(f"Success Rate:   {report.success_rate:.1f}%")
        log_info(f"Avg Retries:    {report.avg_retries:.2f}")
        log_info(f"Avg Time:       {report.avg_time:.2f}s")

        if report.failure_types:
            log_info(f"\nFailure Types:")
            for error_type, count in report.failure_types.items():
                log_info(f"  {error_type}: {count}")

        if report.edge_case_performance:
            log_info(f"\nEdge Case Performance:")
            for case_type, perf in report.edge_case_performance.items():
                log_info(f"  {case_type}: {perf:.1f}%")

        log_info("=" * 60 + "\n")

        return report.model_dump_json(indent=2)
