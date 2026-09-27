import uuid

from sqlalchemy import String, Text, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.database.connection import Base


class Standard(Base):
    __tablename__ = "standards"

    standard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    standard_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    edition_year: Mapped[int | None] = mapped_column(
        nullable=True
    )

    effective_from: Mapped[Date | None] = mapped_column(
        Date,
        nullable=True
    )

    effective_to: Mapped[Date | None] = mapped_column(
        Date,
        nullable=True
    )

    source_document: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )