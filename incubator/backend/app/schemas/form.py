import re

from pydantic import BaseModel, field_validator


class ScreenSpec(BaseModel):
    name: str
    route: str
    description: str


class EntitySpec(BaseModel):
    name: str
    fields: list[str]


class APIRoute(BaseModel):
    method: str
    path: str
    description: str


class EnvVar(BaseModel):
    key: str
    example_value: str
    description: str


class FilePlan(BaseModel):
    path: str
    template: str
    context_keys: list[str]


class FormAnswers(BaseModel):
    app_goal: str
    target_user: str
    top_3_actions: list[str]
    must_have_screens: list[str]
    works_offline: bool
    needs_notifications: bool
    core_data_entities: list[str]
    style_notes: str
    constraints_non_goals: str
    include_payments_placeholder: bool = False
    auth_required: bool = True

    @field_validator("top_3_actions")
    @classmethod
    def must_have_three_actions(cls, v: list[str]) -> list[str]:
        if len(v) < 1:
            raise ValueError("top_3_actions must contain at least 1 item")
        return v


class ProductSpec(BaseModel):
    app_name: str
    app_slug: str

    @field_validator("app_name")
    @classmethod
    def app_name_safe_for_jsx(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9 _-]+$", v):
            raise ValueError("app_name may only contain letters, numbers, spaces, or hyphens")
        return v
    goal: str
    target_user: str
    screens: list[ScreenSpec]
    features: list[str]
    data_entities: list[EntitySpec]
    offline_support: bool
    notifications: bool
    auth_required: bool = True
    payments_placeholder: bool = False
    style_notes: str
    non_goals: list[str]


class ArchitectureBlueprint(BaseModel):
    mobile_framework: str = "expo"
    backend_framework: str = "fastapi"
    selected_modules: list[str]
    file_plan: list[FilePlan]
    api_routes: list[APIRoute]
    db_entities: list[str]
    env_vars: list[EnvVar]
