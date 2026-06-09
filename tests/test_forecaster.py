"""
Tests for the WFMForecaster using an in‑memory database.
Verifies forecast length, prediction storage, and metrics logging.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from app.models.domain import HistoricalFlux, PredictionsTactical, ModelMetrics
from app.services.forecaster import WFMForecaster, INTERVALS_PER_DAY


@pytest.mark.asyncio
async def test_forecast_generates_96_intervals(async_session):
    # Insert some historical data
    now = datetime.now(timezone.utc)
    for i in range(10):
        ts = now - timedelta(hours=i)
        async_session.add(
            HistoricalFlux(
                interval_start=ts,
                call_volume=70,
                aht_seconds=300,
                agents_present=8,
            )
        )
    await async_session.commit()

    forecaster = WFMForecaster(async_session)
    predictions = await forecaster.forecast_next_day()

    assert len(predictions) == INTERVALS_PER_DAY
    # Verify all stored
    stmt = select(PredictionsTactical).where(
        PredictionsTactical.model_version == "hybrid-sim-v1"
    )
    result = await async_session.execute(stmt)
    stored = result.scalars().all()
    assert len(stored) == INTERVALS_PER_DAY

    # Check that a metric was created
    metric_result = await async_session.execute(
        select(ModelMetrics).where(ModelMetrics.metric_name == "rmse_simulated")
    )
    metrics = metric_result.scalars().all()
    assert len(metrics) == 1
    assert metrics[0].metric_value >= 0.0


@pytest.mark.asyncio
async def test_forecast_no_history(async_session):
    """Forecast should work even with an empty history."""
    forecaster = WFMForecaster(async_session)
    predictions = await forecaster.forecast_next_day()
    assert len(predictions) == INTERVALS_PER_DAY
    # All volumes >= 0
    assert all(p.predicted_call_volume >= 0 for p in predictions)