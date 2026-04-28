from datetime import datetime

from pydantic import BaseModel

from app.schemas.form import FormAnswers


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
    product_spec_json: str | None = None
    blueprint_json: str | None = None
    error_summary: str | None = None

    model_config = {"from_attributes": True}


class RunListItem(BaseModel):
    id: str
    status: str
    app_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApproveSpecRequest(BaseModel):
    pass  # spec already stored in DB; approval triggers next stage


class ApproveBlueprintRequest(BaseModel):
    pass  # blueprint already stored in DB; approval triggers next stage


class ApproveShellRequest(BaseModel):
    pass
