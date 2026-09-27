import uuid

from sqlalchemy import String, Text, Float, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.database.connection import Base


class TestCalculation(Base):
    __tablename__ = "test_calculations"

    calculation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    session_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False
    )

    observation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    calculation_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    input_values: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    formula: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    calculated_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    calculation_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    calculated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )