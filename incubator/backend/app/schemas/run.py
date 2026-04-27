from datetime import datetime

from pydantic import BaseModel

from app.schemas.form import ArchitectureBlueprint, FormAnswers, ProductSpec


class CreateRunRequest(BaseModel):
    raw_idea: str
    form_answers: FormAnswers


class RunResponse(BaseModel):
    id: str
    raw_idea: str
    status: str
    app_name: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RunListItem(BaseModel):
    id: str
    status: str
    app_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApproveSpecRequest(BaseModel):
    spec: ProductSpec


class ApproveBlueprintRequest(BaseModel):
    blueprint: ArchitectureBlueprint


class ApproveShellRequest(BaseModel):
    pass  # no body needed — approval is the action
