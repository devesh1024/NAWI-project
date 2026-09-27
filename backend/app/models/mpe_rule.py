import uuid

from sqlalchemy import String, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.connection import Base


class MPERule(Base):
    __tablename__ = "mpe_rules"

    mpe_rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    standard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False
    )

    accuracy_class: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    range_min_e: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    range_max_e: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    mpe_value_e: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    mpe_unit_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    condition: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    test_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    reference_clause: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )