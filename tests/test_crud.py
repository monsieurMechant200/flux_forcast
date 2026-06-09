"""
Unit tests for CRUD operations on domain models using async in-memory SQLite.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from app.models.domain import (
    HistoricalFlux,
    PredictionsTactical,
    ModelMetrics,
    AgentStaffing,
)


@pytest.mark.asyncio
async def test_insert_and_read_historical_flux(async_session):
    ts = datetime(2025, 5, 5, 8, 0, tzinfo=timezone.utc)
    record = HistoricalFlux(
        interval_start=ts,
        call_volume=87,
        aht_seconds=312.5,
        agents_present=8,
    )
    async_session.add(record)
    await async_session.commit()

    stmt = select(HistoricalFlux).where(HistoricalFlux.interval_start == ts)
    result = await async_session.execute(stmt)
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].call_volume == 87
    assert rows[0].aht_seconds == 312.5


@pytest.mark.asyncio
async def test_prediction_tactical_crud(async_session):
    created = datetime.now(timezone.utc)
    interval = datetime(2025, 5, 5, 12, 15, tzinfo=timezone.utc)
    pred = PredictionsTactical(
        created_at=created,
        interval_start=interval,
        predicted_call_volume=120.0,
        predicted_aht=290.0,
        required_agents_net=15.0,
        required_agents_gross=18.2,
        model_version="v1.0.0",
    )
    async_session.add(pred)
    await async_session.commit()

    # Read back
    stmt = select(PredictionsTactical).where(
        PredictionsTactical.interval_start == interval
    )
    result = await async_session.execute(stmt)
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].required_agents_net == 15.0


@pytest.mark.asyncio
async def test_model_metrics_insert(async_session):
    metric = ModelMetrics(
        timestamp=datetime.now(timezone.utc),
        metric_name="rmse",
        metric_value=12.45,
        model_version="v1.0.0",
    )
    async_session.add(metric)
    await async_session.commit()

    stmt = select(ModelMetrics).where(ModelMetrics.metric_name == "rmse")
    result = await async_session.execute(stmt)
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].metric_value == 12.45


@pytest.mark.asyncio
async def test_agent_staffing_insert(async_session):
    interval = datetime(2025, 5, 5, 8, 0, tzinfo=timezone.utc)
    staff = AgentStaffing(
        interval_start=interval,
        agents_scheduled=20,
        agents_actual=18,
    )
    async_session.add(staff)
    await async_session.commit()

    stmt = select(AgentStaffing).where(AgentStaffing.interval_start == interval)
    result = await async_session.execute(stmt)
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].agents_actual == 18