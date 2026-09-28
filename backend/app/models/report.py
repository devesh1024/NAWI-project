import uuid

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.database.connection import Base


class Report(Base):
    __tablename__ = "reports"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    test_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_sessions.test_session_id", ondelete="CASCADE"),
        nullable=False
    )

    report_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    report_version: Mapped[str | None] = mapped_column(
        String(50),
        default="1.0"
    )

    report_status: Mapped[str | None] = mapped_column(
        String(50),
        default="GENERATED"
    )

    overall_result: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=True
    )

    generated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=True
    )

    approved_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    docx_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    pdf_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    report_hash: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    remarks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )