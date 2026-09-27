import uuid

from sqlalchemy import String, Text, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.database.connection import Base


class TestObservation(Base):
    __tablename__ = "test_observations"

    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    session_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False
    )

    parameter_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    parameter_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    value_numeric: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    value_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    observed_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    sequence_no: Mapped[int | None] = mapped_column(
        nullable=True
    )

    source: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    entered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    remarks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )