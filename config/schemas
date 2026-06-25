from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Literal
from enum import Enum


# ============ STAGE 1: INTENT EXTRACTION ============
class UserIntent(BaseModel):
    """Extracted user intent from raw input"""
    app_type: str = Field(..., description="Type of app: CRM, E-commerce, SaaS, etc")
    core_features: List[str] = Field(..., description="Main features user wants")
    user_roles: List[str] = Field(default=["user"], description="Types of users in system")
    authentication_required: bool = Field(default=True, description="Auth needed?")
    payment_required: bool = Field(default=False, description="Payment/premium features?")
    data_requirements: Dict[str, str] = Field(default_factory=dict, description="Key entities")
    constraints: List[str] = Field(default_factory=list, description="Implicit constraints")

    class Config:
        json_schema_extra = {
            "example": {
                "app_type": "CRM",
                "core_features": ["contact_management", "dashboard", "analytics"],
                "user_roles": ["admin", "user"],
                "authentication_required": True,
                "payment_required": True,
                "data_requirements": {"contact": "name, email, phone", "company": "name, industry"},
                "constraints": ["Admin only sees analytics", "Free users limited to 100 contacts"]
            }
        }


# ============ STAGE 2: SYSTEM DESIGN ============
class Entity(BaseModel):
    """Database entity definition"""
    name: str
    fields: Dict[str, str]  # field_name: field_type
    relationships: Optional[List[Dict[str, str]]] = Field(
        default_factory=list)  # { "type": "one-to-many", "target": "User" }

    @validator('name')
    def validate_entity_name(cls, v):
        assert v[0].isupper(), "Entity names must start with uppercase"
        return v


class UserRole(BaseModel):
    """Role definition with permissions"""
    name: str
    description: str
    permissions: List[str]  # e.g., "view_contacts", "create_contact", "delete_contact"
    hierarchy_level: int = Field(default=0, description="0=user, 1=admin, 2=super_admin")


class AppFlow(BaseModel):
    """Key user flow/journey"""
    flow_name: str
    steps: List[str]
    roles_involved: List[str]
    critical: bool = Field(default=False, description="Is this a critical flow?")


class SystemDesign(BaseModel):
    """Complete system architecture"""
    app_name: str
    description: str
    entities: List[Entity]
    roles: List[UserRole]
    flows: List[AppFlow]
    authentication_strategy: Literal["jwt", "session", "oauth"] = "jwt"

    class Config:
        json_schema_extra = {
            "example": {
                "app_name": "CRM System",
                "description": "Customer relationship management",
                "entities": [
                    {"name": "User", "fields": {"id": "uuid", "email": "string", "role": "string"},
                     "relationships": []},
                    {"name": "Contact", "fields": {"id": "uuid", "name": "string", "email": "string"},
                     "relationships": [{"type": "many-to-one", "target": "User"}]}
                ],
                "roles": [{"name": "admin", "description": "Admin user", "permissions": ["*"], "hierarchy_level": 1}],
                "flows": [],
                "authentication_strategy": "jwt"
            }
        }


# ============ STAGE 3: SCHEMA GENERATION ============
class UIComponent(BaseModel):
    """UI component definition"""
    component_id: str
    component_type: Literal["form", "table", "card", "modal", "list", "dashboard"]
    label: str
    fields: List[str]  # Which fields from entities
    visibility_rules: Optional[Dict[str, str]] = Field(default_factory=dict)  # role-based visibility


class UIPage(BaseModel):
    """UI page definition"""
    page_id: str
    page_name: str
    route: str
    allowed_roles: List[str]
    components: List[UIComponent]


class UISchema(BaseModel):
    """Complete UI schema"""
    pages: List[UIPage]
    theme: Optional[Dict[str, str]] = Field(default_factory=dict)

    @validator('pages')
    def validate_unique_routes(cls, v):
        routes = [p.route for p in v]
        assert len(routes) == len(set(routes)), "Duplicate page routes detected"
        return v


class APIEndpoint(BaseModel):
    """API endpoint definition"""
    endpoint_id: str
    path: str
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    description: str
    allowed_roles: List[str]
    request_body_fields: Optional[Dict[str, str]] = Field(default_factory=dict)
    response_fields: Dict[str, str]
    connected_entity: Optional[str] = None  # Links to which entity


class APISchema(BaseModel):
    """Complete API schema"""
    endpoints: List[APIEndpoint]
    base_url: str = "/api/v1"

    @validator('endpoints')
    def validate_unique_paths(cls, v):
        paths = [(e.path, e.method) for e in v]
        assert len(paths) == len(set(paths)), f"Duplicate endpoints detected: {paths}"
        return v


class DBSchema(BaseModel):
    """Database schema (normalized from entities)"""
    tables: Dict[str, Dict[str, str]]  # table_name: { field_name: type }
    relationships: List[Dict[str, str]]  # { from_table, to_table, type }
    indexes: Optional[List[str]] = Field(default_factory=list)


class AuthRules(BaseModel):
    """Authorization rules"""
    role_permissions: Dict[str, List[str]]  # role_name: [permissions]
    entity_access_rules: Dict[str, Dict[str, str]]  # entity: { rule_type: logic }
    premium_gating: Optional[Dict[str, List[str]]] = Field(default_factory=dict)  # feature: [allowed_roles]


class AppConfig(BaseModel):
    """Complete application configuration - THE MASTER OUTPUT"""
    app_id: str
    app_name: str
    version: str = "1.0.0"
    description: str

    # The 4 schemas
    ui_schema: UISchema
    api_schema: APISchema
    db_schema: DBSchema
    auth_rules: AuthRules

    # Metadata
    created_at: str
    prompt_hash: str  # Hash of original prompt for consistency tracking

    class Config:
        json_schema_extra = {
            "description": "Complete application configuration ready for execution"
        }


# ============ VALIDATION & REPAIR ============
class ValidationError(BaseModel):
    """Validation error detail"""
    error_type: Literal["schema_error", "consistency_error", "logic_error", "json_error"]
    location: str  # e.g., "api_schema.endpoints[0]"
    message: str
    severity: Literal["critical", "warning", "info"]
    suggested_fix: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of validation"""
    is_valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    auto_repaired: bool = False
    repair_actions: List[str] = Field(default_factory=list)


# ============ EXECUTION ============
class ExecutionResult(BaseModel):
    """Result of executing config"""
    success: bool
    generated_files: Optional[Dict[str, str]] = None  # filename: code
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ============ EVALUATION ============
class EvaluationMetric(BaseModel):
    """Metrics for single evaluation run"""
    test_case_id: str
    prompt: str
    success: bool
    retries_needed: int
    time_taken_seconds: float
    validation_errors: List[str]
    notes: str


class EvaluationReport(BaseModel):
    """Report on system performance"""
    total_tests: int
    passed: int
    failed: int
    success_rate: float
    avg_retries: float
    avg_time: float
    failure_types: Dict[str, int]  # error_type: count
    edge_case_performance: Dict[str, float]  # edge_case_name: success_rate
