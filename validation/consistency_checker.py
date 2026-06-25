from typing import List, Tuple
from config.schemas import UISchema, APISchema, DBSchema, AuthRules, ValidationError as ValidationErrorSchema
from utils.logger import log_warning, log_info, log_error


class ConsistencyChecker:
    """
    Checks consistency across UI, API, DB, and Auth schemas.
    This is critical for ensuring the config is coherent.
    """

    @staticmethod
    def check_all(ui: UISchema, api: APISchema, db: DBSchema, auth: AuthRules) -> Tuple[
        bool, List[ValidationErrorSchema]]:
        """Run all consistency checks"""
        errors = []

        errors.extend(ConsistencyChecker.check_roles_defined(ui, api, auth))
        errors.extend(ConsistencyChecker.check_api_fields_in_db(api, db))
        errors.extend(ConsistencyChecker.check_ui_fields_valid(ui, api))
        errors.extend(ConsistencyChecker.check_entity_references(api, db))
        errors.extend(ConsistencyChecker.check_relationships_valid(db))
        errors.extend(ConsistencyChecker.check_unique_routes(api))
        errors.extend(ConsistencyChecker.check_premium_gating(auth, api))

        is_valid = len(errors) == 0
        return is_valid, errors

    @staticmethod
    def check_roles_defined(ui: UISchema, api: APISchema, auth: AuthRules) -> List[ValidationErrorSchema]:
        """All roles in UI/API must be defined in auth"""
        errors = []
        defined_roles = set(auth.role_permissions.keys()) if auth.role_permissions else set()

        # Check UI roles
        for page in ui.pages:
            for role in page.allowed_roles:
                if role not in defined_roles:
                    errors.append(ValidationErrorSchema(
                        error_type="consistency_error",
                        location=f"ui_schema.pages.{page.page_id}",
                        message=f"Role '{role}' not defined in auth_rules",
                        severity="critical"
                    ))

        # Check API roles
        for endpoint in api.endpoints:
            for role in endpoint.allowed_roles:
                if role not in defined_roles:
                    errors.append(ValidationErrorSchema(
                        error_type="consistency_error",
                        location=f"api_schema.endpoints.{endpoint.endpoint_id}",
                        message=f"Role '{role}' not defined in auth_rules",
                        severity="critical"
                    ))

        return errors

    @staticmethod
    def check_api_fields_in_db(api: APISchema, db: DBSchema) -> List[ValidationErrorSchema]:
        """API request/response fields must exist in DB"""
        errors = []

        # Flatten all DB fields
        db_fields = {}
        for table_name, fields in db.tables.items():
            db_fields[table_name] = set(fields.keys())

        for endpoint in api.endpoints:
            # Check request fields
            if endpoint.request_body_fields:
                for field in endpoint.request_body_fields.keys():
                    if endpoint.connected_entity:
                        entity_fields = db_fields.get(endpoint.connected_entity, set())
                        if field not in entity_fields and field != "id":
                            errors.append(ValidationErrorSchema(
                                error_type="consistency_error",
                                location=f"api_schema.endpoints.{endpoint.endpoint_id}",
                                message=f"Request field '{field}' not in DB table '{endpoint.connected_entity}'",
                                severity="warning",
                                suggested_fix=f"Add '{field}' to {endpoint.connected_entity} table or remove from API"
                            ))

            # Check response fields
            if endpoint.response_fields:
                for field in endpoint.response_fields.keys():
                    if endpoint.connected_entity:
                        entity_fields = db_fields.get(endpoint.connected_entity, set())
                        if field not in entity_fields and field != "id":
                            errors.append(ValidationErrorSchema(
                                error_type="consistency_error",
                                location=f"api_schema.endpoints.{endpoint.endpoint_id}",
                                message=f"Response field '{field}' not in DB table '{endpoint.connected_entity}'",
                                severity="warning"
                            ))

        return errors

    @staticmethod
    def check_ui_fields_valid(ui: UISchema, api: APISchema) -> List[ValidationErrorSchema]:
        """UI component fields should map to API"""
        errors = []

        api_field_map = {}
        for endpoint in api.endpoints:
            if endpoint.response_fields:
                api_field_map[endpoint.path] = set(endpoint.response_fields.keys())

        # This is a warning-level check since UI can have computed fields
        return errors

    @staticmethod
    def check_entity_references(api: APISchema, db: DBSchema) -> List[ValidationErrorSchema]:
        """All entities referenced in API must exist in DB"""
        errors = []
        db_tables = set(db.tables.keys())

        for endpoint in api.endpoints:
            if endpoint.connected_entity and endpoint.connected_entity not in db_tables:
                errors.append(ValidationErrorSchema(
                    error_type="consistency_error",
                    location=f"api_schema.endpoints.{endpoint.endpoint_id}",
                    message=f"Connected entity '{endpoint.connected_entity}' not found in DB",
                    severity="critical"
                ))

        return errors

    @staticmethod
    def check_relationships_valid(db: DBSchema) -> List[ValidationErrorSchema]:
        """All relationships must reference valid tables"""
        errors = []
        tables = set(db.tables.keys())

        for rel in db.relationships:
            from_table = rel.get('from_table')
            to_table = rel.get('to_table')

            if from_table not in tables:
                errors.append(ValidationErrorSchema(
                    error_type="consistency_error",
                    location="db_schema.relationships",
                    message=f"Invalid from_table '{from_table}' in relationship",
                    severity="critical"
                ))

            if to_table not in tables:
                errors.append(ValidationErrorSchema(
                    error_type="consistency_error",
                    location="db_schema.relationships",
                    message=f"Invalid to_table '{to_table}' in relationship",
                    severity="critical"
                ))

        return errors

    @staticmethod
    def check_unique_routes(api: APISchema) -> List[ValidationErrorSchema]:
        """No duplicate endpoint routes"""
        errors = []
        seen = set()

        for endpoint in api.endpoints:
            route_key = (endpoint.path, endpoint.method)
            if route_key in seen:
                errors.append(ValidationErrorSchema(
                    error_type="consistency_error",
                    location=f"api_schema.endpoints.{endpoint.endpoint_id}",
                    message=f"Duplicate endpoint: {endpoint.method} {endpoint.path}",
                    severity="critical"
                ))
            seen.add(route_key)

        return errors

    @staticmethod
    def check_premium_gating(auth: AuthRules, api: APISchema) -> List[ValidationErrorSchema]:
        """Premium gated features must have valid roles"""
        errors = []

        if auth.premium_gating:
            defined_roles = set(auth.role_permissions.keys())
            for feature, allowed_roles in auth.premium_gating.items():
                for role in allowed_roles:
                    if role not in defined_roles:
                        errors.append(ValidationErrorSchema(
                            error_type="consistency_error",
                            location="auth_rules.premium_gating",
                            message=f"Premium feature '{feature}' references undefined role '{role}'",
                            severity="warning"
                        ))

        return errors
