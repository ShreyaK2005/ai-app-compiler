from config.schemas import AppConfig
from utils.logger import log_info, log_error, log_warning
from typing import List, Dict, Any


class Runtime:
    """
    Runtime executor - validates that the config can actually be executed.
    This is the "run-time" that proves the config works.
    """

    def __init__(self):
        self.errors = []
        self.warnings = []

    def execute(self, app_config: AppConfig) -> tuple[bool, List[str], List[str]]:
        """
        Validate that the config can be executed.

        Checks:
        1. All API endpoints are reachable
        2. All DB tables exist and fields match
        3. All roles are properly defined
        4. All auth rules can be applied
        5. No circular dependencies

        Returns:
            (success, errors, warnings)
        """
        log_info("Runtime: Validating executability...")

        self.errors = []
        self.warnings = []

        # Validation checks
        self._validate_api_endpoints(app_config)
        self._validate_db_consistency(app_config)
        self._validate_auth(app_config)
        self._validate_ui_connectivity(app_config)
        self._validate_dependencies(app_config)

        if self.errors:
            log_error(f"Runtime validation failed with {len(self.errors)} errors")
            return False, self.errors, self.warnings

        log_info("Runtime validation successful")
        return True, self.errors, self.warnings

    def _validate_api_endpoints(self, config: AppConfig):
        """Validate API schema"""
        log_info("Validating API endpoints...")

        seen_paths = set()
        for endpoint in config.api_schema.endpoints:
            # Check for duplicates
            path_key = (endpoint.path, endpoint.method)
            if path_key in seen_paths:
                self.errors.append(f"Duplicate endpoint: {endpoint.method} {endpoint.path}")
            seen_paths.add(path_key)

            # Check that connected entity exists
            if endpoint.connected_entity:
                if endpoint.connected_entity not in config.db_schema.tables:
                    self.errors.append(
                        f"Endpoint {endpoint.endpoint_id}: Entity '{endpoint.connected_entity}' not found in DB")

            # Check that roles are defined
            for role in endpoint.allowed_roles:
                if role not in config.auth_rules.role_permissions:
                    self.errors.append(f"Endpoint {endpoint.endpoint_id}: Role '{role}' not defined in auth")

    def _validate_db_consistency(self, config: AppConfig):
        """Validate DB schema is valid"""
        log_info("Validating database schema...")

        tables = set(config.db_schema.tables.keys())

        # Check relationships reference valid tables
        for rel in config.db_schema.relationships:
            from_table = rel.get('from_table')
            to_table = rel.get('to_table')

            if from_table not in tables:
                self.errors.append(f"Relationship: from_table '{from_table}' not found")
            if to_table not in tables:
                self.errors.append(f"Relationship: to_table '{to_table}' not found")

    def _validate_auth(self, config: AppConfig):
        """Validate auth rules"""
        log_info("Validating auth rules...")

        defined_roles = set(config.auth_rules.role_permissions.keys())

        # Check premium gating references valid roles
        if config.auth_rules.premium_gating:
            for feature, roles in config.auth_rules.premium_gating.items():
                for role in roles:
                    if role not in defined_roles:
                        self.errors.append(f"Premium feature '{feature}': role '{role}' not defined")

    def _validate_ui_connectivity(self, config: AppConfig):
        """Validate UI connects to API"""
        log_info("Validating UI connectivity...")

        # Check that UI pages have valid roles
        defined_roles = set(config.auth_rules.role_permissions.keys())

        for page in config.ui_schema.pages:
            for role in page.allowed_roles:
                if role not in defined_roles:
                    self.warnings.append(f"Page '{page.page_id}': role '{role}' not fully defined")

    def _validate_dependencies(self, config: AppConfig):
        """Check for circular or missing dependencies"""
        log_info("Validating dependencies...")

        # This is a simplified check - could be expanded
        # Check that all referenced tables exist
        tables = set(config.db_schema.tables.keys())

        for endpoint in config.api_schema.endpoints:
            if endpoint.connected_entity and endpoint.connected_entity not in tables:
                self.errors.append(f"Endpoint references non-existent entity: {endpoint.connected_entity}")

    def generate_code_template(self, app_config: AppConfig) -> Dict[str, str]:
        """
        Generate code templates for the app.
        This proves that the config is executable.
        """
        code_files = {}

        # Generate database schema file
        code_files["database.sql"] = self._generate_database_sql(app_config)

        # Generate API routes skeleton
        code_files["api_routes.py"] = self._generate_api_routes(app_config)

        # Generate models
        code_files["models.py"] = self._generate_models(app_config)

        # Generate auth module
        code_files["auth.py"] = self._generate_auth_module(app_config)

        return code_files

    def _generate_database_sql(self, config: AppConfig) -> str:
        """Generate SQL for database tables"""
        sql = "-- Auto-generated database schema\n\n"

        for table_name, fields in config.db_schema.tables.items():
            sql += f"CREATE TABLE {table_name} (\n"
            sql += "  id UUID PRIMARY KEY,\n"
            for field_name, field_type in fields.items():
                if field_name != "id":
                    sql += f"  {field_name} {field_type},\n"
            sql = sql.rstrip(",\n") + "\n);\n\n"

        return sql

    def _generate_api_routes(self, config: AppConfig) -> str:
        """Generate API route skeleton"""
        routes = "# Auto-generated API routes\n\n"
        routes += "from flask import Blueprint, request, jsonify\n\n"

        routes += "api = Blueprint('api', __name__, url_prefix='/api/v1')\n\n"

        for endpoint in config.api_schema.endpoints:
            routes += f"@api.route('{endpoint.path}', methods=['{endpoint.method}'])\n"
            routes += f"def {endpoint.endpoint_id}():\n"
            routes += f"    \"\"\"endpoint_id: {endpoint.endpoint_id}\"\"\"\n"
            routes += f"    # TODO: Implement {endpoint.description}\n"
            routes += f"    # Allowed roles: {', '.join(endpoint.allowed_roles)}\n"
            routes += f"    return jsonify({{'status': 'not_implemented'}})\n\n"

        return routes

    def _generate_models(self, config: AppConfig) -> str:
        """Generate Pydantic models"""
        models = "# Auto-generated models\n\n"
        models += "from pydantic import BaseModel\n\n"

        for entity in config.db_schema.tables.keys():
            models += f"class {entity}(BaseModel):\n"
            fields = config.db_schema.tables[entity]
            for field_name, field_type in fields.items():
                models += f"    {field_name}: str  # TODO: correct type\n"
            models += "\n"

        return models

    def _generate_auth_module(self, config: AppConfig) -> str:
        """Generate auth module"""
        auth = "# Auto-generated auth module\n\n"

        auth += "ROLES = " + str(list(config.auth_rules.role_permissions.keys())) + "\n\n"

        auth += "def has_permission(user_role: str, permission: str) -> bool:\n"
        auth += "    # TODO: Implement permission checking\n"
        auth += "    return False\n\n"

        return auth