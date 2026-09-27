import uuid

from sqlalchemy import String, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.connection import Base


class TestApplicabilityRule(Base):
    __tablename__ = "test_applicability_rules"

    applicability_rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    test_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False
    )

    instrument_condition: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    applicable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    priority: Mapped[int | None] = mapped_column(
        nullable=True
    )

    standard_clause: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )