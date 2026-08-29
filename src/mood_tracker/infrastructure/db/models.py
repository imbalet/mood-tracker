"""SQLAlchemy mappings for the durable diary model."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Interval,
    Numeric,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM mappings."""


class Timestamped:
    """UTC timestamps managed by PostgreSQL."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UserOrm(Timestamped, Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)


class NotificationSettingsOrm(Timestamped, Base):
    __tablename__ = "notification_settings"
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), primary_key=True, nullable=False
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminder_time: Mapped[time] = mapped_column(Time, nullable=False)
    repeat_interval: Mapped[timedelta] = mapped_column(Interval, nullable=False)
    max_reminders_per_day: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class NotificationDeliveriesOrm(Base):
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "local_date",
            "reminder_number",
            name="notification_delivery_user_date_reminder_key",
        ),
        CheckConstraint(
            "status IN ('claimed', 'sent')", name="notification_delivery_status_check"
        ),
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), primary_key=True, nullable=False
    )
    local_date: Mapped[date] = mapped_column(Date, primary_key=True, nullable=False)
    reminder_number: Mapped[int] = mapped_column(
        SmallInteger, primary_key=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class FieldOrm(Timestamped, Base):
    __tablename__ = "fields"
    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    current_version_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "field_versions.id",
            name="fields_current_version_fkey",
            use_alter=True,
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
    )
    display_config: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB, nullable=False
    )


class FieldVersionOrm(Base):
    __tablename__ = "field_versions"
    __table_args__ = (
        CheckConstraint(
            "type IN ('scale', 'ordinal', 'text')", name="field_versions_type_check"
        ),
    )
    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    field_id: Mapped[UUID] = mapped_column(ForeignKey("fields.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(postgresql.JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class QuestionnaireOrm(Timestamped, Base):
    __tablename__ = "questionnaires"
    __table_args__ = (
        UniqueConstraint("user_id", "kind", name="questionnaires_user_kind_key"),
    )
    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)


class QuestionnaireFieldOrm(Base):
    __tablename__ = "questionnaire_fields"
    __table_args__ = (
        UniqueConstraint(
            "questionnaire_id", "field_id", name="questionnaire_fields_key"
        ),
        UniqueConstraint(
            "questionnaire_id",
            "sort_order",
            name="questionnaire_fields_questionnaire_order_key",
        ),
        CheckConstraint("sort_order >= 0", name="questionnaire_fields_order_check"),
    )
    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    questionnaire_id: Mapped[UUID] = mapped_column(
        ForeignKey("questionnaires.id"), nullable=False
    )
    field_id: Mapped[UUID] = mapped_column(ForeignKey("fields.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DayOrm(Timestamped, Base):
    __tablename__ = "days"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="days_user_date_key"),
        CheckConstraint("status IN ('draft', 'complete')", name="days_status_check"),
    )
    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DayValueOrm(Timestamped, Base):
    __tablename__ = "day_values"
    __table_args__ = (
        UniqueConstraint("day_id", "field_id", name="day_values_day_field_key"),
        CheckConstraint(
            "normalized_value IS NULL OR normalized_value BETWEEN 0 AND 1",
            name="day_values_normalized_check",
        ),
    )
    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    day_id: Mapped[UUID] = mapped_column(ForeignKey("days.id"), nullable=False)
    field_id: Mapped[UUID] = mapped_column(ForeignKey("fields.id"), nullable=False)
    field_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("field_versions.id"), nullable=False
    )
    value: Mapped[dict[str, Any]] = mapped_column(postgresql.JSONB, nullable=False)
    normalized_value: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )


class DayFieldProgressOrm(Base):
    __tablename__ = "day_field_progress"
    __table_args__ = (
        UniqueConstraint("day_id", "field_id", name="day_field_progress_day_field_key"),
    )
    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    day_id: Mapped[UUID] = mapped_column(ForeignKey("days.id"), nullable=False)
    field_id: Mapped[UUID] = mapped_column(ForeignKey("fields.id"), nullable=False)
    field_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("field_versions.id"), nullable=False
    )
    skipped: Mapped[bool] = mapped_column(Boolean, nullable=False)


class EventOrm(Timestamped, Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'complete')", name="events_status_check"),
    )
    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    occurred_timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EventValueOrm(Timestamped, Base):
    __tablename__ = "event_values"
    __table_args__ = (
        UniqueConstraint("event_id", "field_id", name="event_values_event_field_key"),
        CheckConstraint(
            "normalized_value IS NULL OR normalized_value BETWEEN 0 AND 1",
            name="event_values_normalized_check",
        ),
    )
    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), nullable=False)
    field_id: Mapped[UUID] = mapped_column(ForeignKey("fields.id"), nullable=False)
    field_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("field_versions.id"), nullable=False
    )
    value: Mapped[dict[str, Any]] = mapped_column(postgresql.JSONB, nullable=False)
    normalized_value: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))


class EventFieldProgressOrm(Base):
    __tablename__ = "event_field_progress"
    __table_args__ = (
        UniqueConstraint("event_id", "field_id", name="event_progress_event_field_key"),
    )
    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), nullable=False)
    field_id: Mapped[UUID] = mapped_column(ForeignKey("fields.id"), nullable=False)
    field_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("field_versions.id"), nullable=False
    )
    skipped: Mapped[bool] = mapped_column(Boolean, nullable=False)


class ReferenceStateOrm(Timestamped, Base):
    __tablename__ = "reference_states"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    best_day_id: Mapped[UUID | None] = mapped_column(ForeignKey("days.id"))
    worst_day_id: Mapped[UUID | None] = mapped_column(ForeignKey("days.id"))


class DayReferenceOrm(Base):
    __tablename__ = "day_references"
    __table_args__ = (
        CheckConstraint("type IN ('best', 'worst')", name="day_references_type_check"),
    )
    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    day_id: Mapped[UUID] = mapped_column(ForeignKey("days.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    previous_reference_day_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("days.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
