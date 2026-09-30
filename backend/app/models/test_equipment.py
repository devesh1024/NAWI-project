import uuid

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.database.connection import Base


class TestEquipment(Base):
    __tablename__ = "test_equipment"

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    laboratory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("laboratories.laboratory_id", ondelete="CASCADE"),
        nullable=False
    )

    equipment_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    equipment_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    serial_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    identification_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    calibration_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    calibration_date: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    calibration_due_date: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
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