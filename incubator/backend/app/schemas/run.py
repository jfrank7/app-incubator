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

    model_config = {"from_attributes": True}


class RunListItem(BaseModel):
    id: str
    status: str
    app_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
