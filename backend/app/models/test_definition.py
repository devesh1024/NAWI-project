import uuid

from sqlalchemy import String, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.connection import Base


class TestDefinition(Base):
    __tablename__ = "test_definitions"

    test_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    standard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False
    )

    test_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    test_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    reference_clause: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    procedure: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    required_inputs: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    calculation_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    acceptance_rule: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    required_equipment: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )