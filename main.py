from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import json
from pipeline.coordinator import PipelineCoordinator
from execution.runtime import Runtime
from evaluation.evaluator import Evaluator
from utils.logger import log_info, log_error
from config.constants import GROQ_API_KEY

print("API Key loaded:", GROQ_API_KEY[:15] if GROQ_API_KEY else None)

# Initialize Flask app
app = Flask(__name__, template_folder='templates')
CORS(app)

# Initialize pipeline and runtime
coordinator = PipelineCoordinator()
runtime = Runtime()
evaluator = Evaluator()


@app.route('/')
def index():
    """Serve the web UI"""
    return render_template('index.html')


@app.route('/api/compile', methods=['POST'])
def compile_app():
    """
    API endpoint to compile an app from natural language prompt.

    Request:
        {
            "prompt": "Build a CRM with..."
        }

    Response:
        {
            "success": bool,
            "app_id": str,
            "app_name": str,
            "elapsed_seconds": float,
            "api_endpoints": int,
            "db_tables": int,
            "config": {full AppConfig JSON}
        }
    """
    try:
        data = request.get_json()
        prompt = data.get('prompt', '').strip()

        if not prompt:
            return jsonify({"success": False, "error": "Empty prompt"}), 400

        log_info(f"Received compilation request: {prompt[:100]}...")

        # Run the full pipeline
        success, app_config, details = coordinator.process(prompt)

        if not success:
            log_error(f"Compilation failed: {details}")
            return jsonify({
                "success": False,
                "error": details.get("error", "Pipeline failed")
            }), 400

        # Validate with runtime
        runtime_success, runtime_errors, runtime_warnings = runtime.execute(app_config)

        if not runtime_success:
            log_error(f"Runtime validation failed: {runtime_errors}")
            return jsonify({
                "success": False,
                "error": f"Runtime validation failed: {', '.join(runtime_errors)}"
            }), 400

        # Generate code templates
        code_files = runtime.generate_code_template(app_config)

        # Prepare response
        response = {
            "success": True,
            "app_id": app_config.app_id,
            "app_name": app_config.app_name,
            "elapsed_seconds": details.get("elapsed_seconds", 0),
            "api_endpoints": len(app_config.api_schema.endpoints),
            "db_tables": len(app_config.db_schema.tables),
            "ui_pages": len(app_config.ui_schema.pages),
            "config": json.loads(app_config.model_dump_json()),
            "code_templates": code_files
        }

        log_info(f"✓ Compilation successful: App ID {app_config.app_id}")
        return jsonify(response), 200

    except Exception as e:
        log_error(f"Endpoint error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500


@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    """
    Run evaluation on all test cases.
    Returns metrics and performance report.
    """
    try:
        log_info("Starting evaluation run...")

        # Run all tests
        report = evaluator.run_all_tests()

        # Print report
        report_text = evaluator.print_report(report)

        response = {
            "success": True,
            "total_tests": report.total_tests,
            "passed": report.passed,
            "failed": report.failed,
            "success_rate": report.success_rate,
            "avg_retries": report.avg_retries,
            "avg_time": report.avg_time,
            "failure_types": report.failure_types,
            "edge_case_performance": report.edge_case_performance,
            "metrics": [m.model_dump() for m in evaluator.metrics]
        }

        return jsonify(response), 200

    except Exception as e:
        log_error(f"Evaluation error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "app_compiler",
        "version": "1.0.0"
    }), 200


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Server error"}), 500


def setup_directories():
    """Create necessary directories"""
    os.makedirs('templates', exist_ok=True)
    os.makedirs('logs', exist_ok=True)


if __name__ == '__main__':
    setup_directories()

    log_info("=" * 60)
    log_info("APP COMPILER - Starting Flask Server")
    log_info("=" * 60)
    log_info("Available endpoints:")
    log_info("  GET  /                    - Web UI")
    log_info("  POST /api/compile         - Compile app from prompt")
    log_info("  POST /api/evaluate        - Run evaluation tests")
    log_info("  GET  /api/health          - Health check")
    log_info("=" * 60)

    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False
    )
