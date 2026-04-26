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
        if len(v) != 3:
            raise ValueError("top_3_actions must contain exactly 3 items")
        return v


class ProductSpec(BaseModel):
    app_name: str
    app_slug: str
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
