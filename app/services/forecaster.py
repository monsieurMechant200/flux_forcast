"""
Simulated hybrid forecaster (SARIMA + XGBoost residuals) for WFM.
Can generate predictions for the next N days.
"""

import asyncio
import math
import random
import logging
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import PredictionsTactical, ModelMetrics
from app.models.database import async_session_factory

logger = logging.getLogger(__name__)
INTERVALS_PER_DAY = 96
MODEL_VERSION = "hybrid-sim-v1"


class WFMForecaster:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_recent_history(self, hours_back: int = 24) -> list:
        from app.models.domain import HistoricalFlux
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        stmt = (
            select(HistoricalFlux)
            .where(HistoricalFlux.interval_start >= cutoff)
            .order_by(HistoricalFlux.interval_start)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    def _simulate_sarima_forecast(
        self, start_ts: datetime, length: int, base_history: list
    ) -> List[float]:
        forecast = []
        for i in range(length):
            ts = start_ts + timedelta(minutes=15 * i)
            hour = ts.hour + ts.minute / 60.0
            daily_phase = (hour - 10) / 24 * 2 * math.pi
            daily_component = 50 + 30 * math.cos(daily_phase)
            weekday = ts.weekday()
            weekly_factor = 0.65 if weekday >= 5 else 1.0
            hist_avg = 60.0
            if base_history:
                hist_avg = sum(h.call_volume for h in base_history) / max(1, len(base_history))
            base = daily_component * weekly_factor * (hist_avg / 60.0)
            noise = random.gauss(0, 5)
            forecast.append(max(0.0, base + noise))
        return forecast

    def _simulate_xgboost_residual_correction(self, ts: datetime, base_pred: float) -> float:
        if ts.weekday() == 0 and 9 <= ts.hour < 10:
            return base_pred + random.uniform(10, 25)
        if ts.weekday() == 4 and 14 <= ts.hour < 16:
            return base_pred * 0.95
        return base_pred

    async def forecast_next_day(self) -> List[PredictionsTactical]:
        """Generate predictions for the next 24 hours (96 intervals)."""
        return await self._forecast_days(1)

    async def forecast_next_days(self, days: int) -> List[PredictionsTactical]:
        """Generate predictions for the next `days` days (96 intervals per day)."""
        return await self._forecast_days(days)

    async def _forecast_days(self, days: int) -> List[PredictionsTactical]:
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        minute_block = (now.minute // 15) * 15
        aligned_now = now.replace(minute=minute_block)

        # We use recent history for the simulation
        history = await self._get_recent_history()

        total_intervals = days * INTERVALS_PER_DAY
        raw_forecast = self._simulate_sarima_forecast(aligned_now, total_intervals, history)

        predictions = []
        for i, base_val in enumerate(raw_forecast):
            interval_ts = aligned_now + timedelta(minutes=15 * i)
            corrected = self._simulate_xgboost_residual_correction(interval_ts, base_val)
            aht = min(320.0, 420)
            predictions.append(
                PredictionsTactical(
                    created_at=now,
                    interval_start=interval_ts,
                    predicted_call_volume=round(corrected, 2),
                    predicted_aht=aht,
                    required_agents_net=None,
                    required_agents_gross=None,
                    model_version=MODEL_VERSION,
                )
            )

        self.session.add_all(predictions)
        await self.session.commit()

        # Store a metric (based on the first prediction vs last historical point)
        metric_value = 0.0
        if history:
            last_real = history[-1].call_volume
            first_pred = predictions[0].predicted_call_volume
            metric_value = (last_real - first_pred) ** 2

        metric = ModelMetrics(
            timestamp=now,
            metric_name="rmse_simulated",
            metric_value=math.sqrt(metric_value),
            model_version=MODEL_VERSION,
        )
        self.session.add(metric)
        await self.session.commit()

        logger.info(
            "Forecast generated for %d intervals (next %d days). Pseudo-RMSE: %.4f",
            len(predictions), days, metric.metric_value,
        )
        return predictions


async def run_forecast_pipeline():
    """Run daily forecast for the next 24 hours (and optionally pre-compute week)."""
    async with async_session_factory() as session:
        forecaster = WFMForecaster(session)
        # Run 1-day forecast for today's dashboard
        await forecaster.forecast_next_day()
        # Run 7-day forecast for planning (can be cached)
        await forecaster.forecast_next_days(7)