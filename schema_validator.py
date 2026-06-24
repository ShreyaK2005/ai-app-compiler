import json
from pydantic import ValidationError, BaseModel
from typing import Type, Tuple, List
from config.schemas import (
    UserIntent,
    SystemDesign,
    UISchema,
    APISchema,
    DBSchema,
    AuthRules,
    AppConfig,
    ValidationError as ValidationErrorSchema,
    ValidationResult
)
from utils.logger import log_error, log_warning, log_info


class SchemaValidator:
    """Validates LLM outputs against Pydantic schemas"""

    @staticmethod
    def validate_intent(data: dict) -> Tuple[bool, UserIntent, List[str]]:
        """Validate Stage 1 output"""
        try:
            intent = UserIntent(**data)
            return True, intent, []
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return False, None, errors

    @staticmethod
    def validate_design(data: dict) -> Tuple[bool, SystemDesign, List[str]]:
        """Validate Stage 2 output"""
        try:
            design = SystemDesign(**data)
            return True, design, []
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return False, None, errors

    @staticmethod
    def validate_ui_schema(data: dict) -> Tuple[bool, UISchema, List[str]]:
        """Validate UI schema"""
        try:
            schema = UISchema(**data)
            return True, schema, []
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return False, None, errors

    @staticmethod
    def validate_api_schema(data: dict) -> Tuple[bool, APISchema, List[str]]:
        """Validate API schema"""
        try:
            schema = APISchema(**data)
            return True, schema, []
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return False, None, errors

    @staticmethod
    def validate_db_schema(data: dict) -> Tuple[bool, DBSchema, List[str]]:
        """Validate DB schema"""
        try:
            schema = DBSchema(**data)
            return True, schema, []
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return False, None, errors

    @staticmethod
    def validate_auth_rules(data: dict) -> Tuple[bool, AuthRules, List[str]]:
        """Validate auth rules"""
        try:
            rules = AuthRules(**data)
            return True, rules, []
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return False, None, errors

    @staticmethod
    def validate_app_config(data: dict) -> Tuple[bool, AppConfig, List[str]]:
        """Validate complete app config"""
        try:
            config = AppConfig(**data)
            return True, config, []
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return False, None, errors

    @staticmethod
    def validate_pydantic_model(model: Type[BaseModel], data: dict) -> Tuple[bool, BaseModel, List[str]]:
        """Generic pydantic validation"""
        try:
            instance = model(**data)
            return True, instance, []
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return False, None, errors