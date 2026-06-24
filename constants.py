import os
from dotenv import load_dotenv

load_dotenv()

# ============ LLM CONFIG ============
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-5"
MAX_TOKENS = 4096
TEMPERATURE = 0.7

# ============ RETRY CONFIG ============
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2

# ============ VALIDATION CONFIG ============
ALLOW_AUTO_REPAIR = True
REPAIR_MAX_ATTEMPTS = 2
STRICT_MODE = True  # If True, warnings become errors

# ============ ERROR TYPES ============
ERROR_TYPES = {
    "JSON_PARSE_ERROR": "Failed to parse JSON",
    "SCHEMA_VALIDATION_ERROR": "Output doesn't match schema",
    "CONSISTENCY_ERROR": "Cross-layer inconsistency detected",
    "MISSING_REQUIRED_FIELDS": "Required fields missing",
    "HALLUCINATED_FIELDS": "Unexpected fields in output",
    "LOGIC_ERROR": "Logical inconsistency",
    "EXECUTION_ERROR": "Failed to execute config"
}
# ============ STAGE PROMPTS ============
STAGE_PROMPTS = {
    "intent_extraction": """You are an expert at understanding product requirements from natural language.

Extract the user's intent from the following prompt and output ONLY valid JSON (no preamble, no explanation).

The JSON must strictly follow this structure:
{
    "app_type": "string (e.g., CRM, E-commerce, SaaS, etc)",
    "core_features": ["list of main features"],
    "user_roles": ["list of user types in the system"],
    "authentication_required": boolean,
    "payment_required": boolean,
    "data_requirements": {"entity_name": "description of fields"},
    "constraints": ["list of constraints/rules from the prompt"]
}

User Prompt:
{prompt}

Output ONLY the JSON, nothing else.""",

    "system_design": """You are a system architect. Given the user intent, design a complete system architecture.

Output ONLY valid JSON (no preamble).

Structure:
{
    "app_name": "string",
    "description": "string",
    "entities": [
        {
            "name": "EntityName",
            "fields": {"field_name": "type"},
            "relationships": [{"type": "one-to-many|many-to-one|one-to-one", "target": "OtherEntity"}]
        }
    ],
    "roles": [
        {
            "name": "role_name",
            "description": "string",
            "permissions": ["list of actions"],
            "hierarchy_level": 0
        }
    ],
    "flows": [
        {
            "flow_name": "string",
            "steps": ["step1", "step2"],
            "roles_involved": ["role1"],
            "critical": false
        }
    ],
    "authentication_strategy": "jwt"
}

Intent:
{intent_json}

Output ONLY the JSON.""",

    "schema_generation": """You are a schema generator. Convert system design into concrete UI, API, and DB schemas.

Output ONLY valid JSON (no preamble).

For UI pages, for each core feature mentioned, create a page. For API, create endpoints for CRUD operations.
For DB, normalize entities into tables. For auth, map roles to permissions.

Return this exact structure (fill in the details based on the design):
{
    "ui_schema": {
        "pages": [],
        "theme": {}
    },
    "api_schema": {
        "base_url": "/api/v1",
        "endpoints": []
    },
    "db_schema": {
        "tables": {},
        "relationships": [],
        "indexes": []
    },
    "auth_rules": {
        "role_permissions": {},
        "entity_access_rules": {},
        "premium_gating": {}
    }
}

Design:
{design_json}

Output ONLY the JSON.""",

    "refinement": """You are a consistency checker and repair expert. 

Given these schemas, fix ALL inconsistencies:
1. Every field in API request/response must exist in DB or UI
2. Every role referenced must be defined in auth_rules
3. Every entity referenced must exist
4. All table relationships must be valid (foreign keys)
5. No duplicate endpoints or pages
6. All component fields must map to actual data

Be thorough. Return ONLY the corrected JSON with all issues fixed.

Return this structure:
{
    "ui_schema": {...full fixed schema...},
    "api_schema": {...full fixed schema...},
    "db_schema": {...full fixed schema...},
    "auth_rules": {...full fixed schema...}
}

Current Config:
{config_json}

Output ONLY the corrected JSON. No explanations."""
}

# ============ TEST CASES ============
TEST_CASES = [
    {"id": "test_001", "type": "real",
     "prompt": "Build a CRM with login, contacts, dashboard, role-based access, and premium plan with payments. Admins can see analytics."},
    {"id": "test_002", "type": "real",
     "prompt": "Create an e-commerce platform with product catalog, shopping cart, checkout, payment processing, order tracking, and admin panel."},
    {"id": "test_003", "type": "real",
     "prompt": "Build a task management app with projects, tasks, subtasks, team collaboration, comments, and deadline tracking."},
    {"id": "test_004", "type": "real",
     "prompt": "Create a SaaS analytics dashboard that aggregates data, shows real-time metrics, allows custom reports, and supports multi-tenant accounts."},
    {"id": "test_005", "type": "real",
     "prompt": "Build a HR management system with employee profiles, leave management, payroll, performance reviews, and document storage."},
    {"id": "test_006", "type": "real",
     "prompt": "Create a social media feed with posts, comments, likes, profiles, follow system, notifications, and trending content."},
    {"id": "test_007", "type": "real",
     "prompt": "Build a project management tool with Gantt charts, resource allocation, risk tracking, budget management, and team communication."},
    {"id": "test_008", "type": "real",
     "prompt": "Create a content management system with WYSIWYG editor, media library, publishing workflows, SEO tools, and analytics."},
    {"id": "test_009", "type": "real",
     "prompt": "Build a booking platform for services with calendar management, customer profiles, invoicing, payment processing, and review system."},
    {"id": "test_010", "type": "real",
     "prompt": "Create a learning management system with courses, lessons, quizzes, progress tracking, certificates, and instructor tools."},

    # ===== EDGE CASES =====
    {"id": "test_011", "type": "edge_vague", "prompt": "Build something useful for a team"},
    {"id": "test_012", "type": "edge_conflicting",
     "prompt": "Create a CRM but it should be simple with just basic features, and also include advanced ML-based predictive analytics and real-time collaboration with 1000s of concurrent users"},
    {"id": "test_013", "type": "edge_incomplete", "prompt": "An app with users and data"},
    {"id": "test_014", "type": "edge_ambiguous", "prompt": "Build what Instagram does but for documents"},
    {"id": "test_015", "type": "edge_technical",
     "prompt": "Create a system that supports GraphQL, REST, and gRPC APIs simultaneously with real-time updates using WebSockets"},
    {"id": "test_016", "type": "edge_over_scoped", "prompt": "Build Salesforce"},
    {"id": "test_017", "type": "edge_contradictory",
     "prompt": "Create a simple MVP with no login, but with advanced role-based access control"},
    {"id": "test_018", "type": "edge_minimal", "prompt": "Blog"},
    {"id": "test_019", "type": "edge_implicit",
     "prompt": "I need a system to manage my business but I didn't say what kind"},
    {"id": "test_020", "type": "edge_technical_constraints",
     "prompt": "Build a system that must work offline but also sync data in real-time across 10 devices"}]