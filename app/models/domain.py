"""
Domain models mapping WFM concepts to PostgreSQL/SQLite tables.
Optimised with indexes on timestamps for time-series queries.
"""
from datetime import datetime
from sqlalchemy import Index, String, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class HistoricalFlux(Base):
    __tablename__ = "historical_flux"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interval_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    call_volume: Mapped[int] = mapped_column(Integer, nullable=False)
    aht_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    agents_present: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        Index("ix_historical_flux_interval", "interval_start"),
    )

class PredictionsTactical(Base):
    __tablename__ = "predictions_tactical"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    interval_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    predicted_call_volume: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_aht: Mapped[float] = mapped_column(Float, nullable=False)
    required_agents_net: Mapped[float] = mapped_column(Float, nullable=True)
    required_agents_gross: Mapped[float] = mapped_column(Float, nullable=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    __table_args__ = (
        Index("ix_predictions_tactical_interval", "interval_start"),
        Index("ix_predictions_tactical_created", "created_at"),
    )

class ModelMetrics(Base):
    __tablename__ = "model_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    metric_name: Mapped[str] = mapped_column(String(20), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    __table_args__ = (
        Index("ix_model_metrics_ts", "timestamp"),
    )

class AgentStaffing(Base):
    __tablename__ = "agent_staffing"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interval_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    agents_scheduled: Mapped[int] = mapped_column(Integer, nullable=False)
    agents_actual: Mapped[int] = mapped_column(Integer, nullable=False)

    # Nouveaux champs pour le suivi en temps réel
    agents_on_break_15: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    agents_on_break_60: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    agents_over_aht: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    agents_late: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    agents_finished_shift: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    break_15_return_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    break_60_return_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_agent_staffing_interval", "interval_start"),
    )