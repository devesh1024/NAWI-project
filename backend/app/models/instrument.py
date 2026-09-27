import uuid

from sqlalchemy import String, Text, Float, Integer, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.database.connection import Base


class Instrument(Base):
    __tablename__ = "instruments"

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    laboratory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False
    )

    instrument_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    manufacturer: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    model: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    type_designation: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    serial_number: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    instrument_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    accuracy_class: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    max_capacity: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    min_capacity: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    verification_scale_interval: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    scale_interval: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    number_of_intervals: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    tare_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    zero_setting_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    indication_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    load_cell_info: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    software_firmware: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    power_supply: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    interfaces: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    temperature_min: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    temperature_max: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )