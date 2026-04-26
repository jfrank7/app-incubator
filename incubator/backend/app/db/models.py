from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    raw_idea: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")
    app_name: Mapped[str | None] = mapped_column(String, nullable=True)
    form_answers_json: Mapped[str] = mapped_column(Text)
    product_spec_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    blueprint_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    qa_report_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    stage_logs_json: Mapped[str | None] = mapped_column(Text, nullable=True)
