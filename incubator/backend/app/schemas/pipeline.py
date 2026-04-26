from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal, TypedDict
from pydantic import BaseModel, Field
from app.schemas.form import FormAnswers, ProductSpec, ArchitectureBlueprint, FilePlan


class QACheck(BaseModel):
    name: str
    passed: bool
    output: str
    error: str | None = None


class QAResults(BaseModel):
    passed: bool
    checks: list[QACheck]
    summary: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RunState(TypedDict):
    run_id: str
    raw_idea: str
    form_answers: FormAnswers
    product_spec: ProductSpec | None
    architecture_blueprint: ArchitectureBlueprint | None
    selected_modules: list[str]
    file_plan: list[FilePlan]
    changed_files: list[str]
    qa_results: QAResults | None
    retry_count: int
    error_history: list[str]
    final_status: Literal["pending", "running", "done", "failed"]
    stage_logs: list[dict]
