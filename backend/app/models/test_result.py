import uuid

from sqlalchemy import String, Text, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.database.connection import Base


class TestResult(Base):
    __tablename__ = "test_results"

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    session_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False
    )

    measured_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    mpe_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    error_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    corrected_error: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    acceptance_condition: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    pass_fail: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    result_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    calculation_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    evaluated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )