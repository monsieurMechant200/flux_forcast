"""
FastAPI application serving REST API, static frontend assets,
and background scheduling of the forecast pipeline.
"""

import gc
import logging
import random
import math
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select, func

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.models.database import async_session_factory, init_db
from app.models.domain import PredictionsTactical, HistoricalFlux, AgentStaffing
from app.services.erlang_c import erlang_c_staffing
from app.services.forecaster import run_forecast_pipeline
from app.services.simulator import inject_scenario

setup_logging(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
async def fill_history_today():
    """Inject synthetic historical data from midnight to now, every 15 min."""
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    async with async_session_factory() as session:
        current = start_of_day
        while current < now:
            hour = current.hour
            if 8 <= hour < 18:
                base_vol = random.randint(55, 85)
                agents = random.randint(15, 25)
            elif 6 <= hour < 8 or 18 <= hour < 20:
                base_vol = random.randint(30, 55)
                agents = random.randint(8, 15)
            else:
                base_vol = random.randint(5, 25)
                agents = random.randint(3, 8)

            aht = min(random.uniform(260, 380), 420.0)
            on_break_15 = random.randint(0, max(1, agents // 5))
            on_break_60 = random.randint(0, max(1, agents // 8))
            over_aht = random.randint(0, max(1, agents // 10))
            late = random.randint(0, max(1, agents // 10))
            finished = random.randint(0, max(1, agents // 6))

            break_15_return = current + timedelta(minutes=15) if on_break_15 > 0 else None
            break_60_return = current + timedelta(minutes=60) if on_break_60 > 0 else None

            session.add(HistoricalFlux(
                interval_start=current,
                call_volume=base_vol,
                aht_seconds=aht,
                agents_present=agents,
            ))
            session.add(AgentStaffing(
                interval_start=current,
                agents_scheduled=agents + random.randint(0, 2),
                agents_actual=agents,
                agents_on_break_15=on_break_15,
                agents_on_break_60=on_break_60,
                agents_over_aht=over_aht,
                agents_late=late,
                agents_finished_shift=finished,
                break_15_return_time=break_15_return,
                break_60_return_time=break_60_return,
            ))
            current += timedelta(minutes=15)
        await session.commit()
    logger.info("Historical data filled (with agent states).")


async def scheduled_forecast():
    logger.info("Scheduled forecast pipeline triggered.")
    try:
        await run_forecast_pipeline()
    except Exception:
        logger.exception("Forecast pipeline failed.")
    finally:
        gc.collect()


async def scheduled_injection():
    logger.info("Scheduled data injection triggered.")
    try:
        await inject_scenario("standard")
    except Exception:
        logger.exception("Data injection failed.")
    finally:
        gc.collect()


# ------------------------------------------------------------------
# Application startup / shutdown
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising database and starting scheduler.")
    await init_db()
    scheduler.add_job(scheduled_forecast, "interval", minutes=30, id="forecast")
    scheduler.add_job(scheduled_injection, "interval", minutes=30, id="injection")
    scheduler.start()
    try:
        await fill_history_today()
        await inject_scenario("standard")
        await run_forecast_pipeline()
    except Exception:
        logger.exception("Initial data / forecast failed.")
    yield
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shut down.")


app = FastAPI(
    title="WFM Tactical Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ------------------------------------------------------------------
# Pydantic schemas
# ------------------------------------------------------------------
class LiveKPIOut(BaseModel):
    longest_call_waiting: str
    current_call_waiting: int
    average_talk_time: str
    total_calls_today: int
    agent_ready: int
    agent_logged_in: int
    asa_seconds: int
    abandoned_today: int
    occupancy_pct: float
    service_level_pct: float
    alerts: List[str] = Field(default_factory=list)


class LiveAgentOut(BaseModel):
    agents_actual: int
    agents_scheduled: int
    agents_on_break_15: int
    agents_on_break_60: int
    agents_over_aht: int
    agents_late: int
    agents_finished_shift: int
    break_15_remaining_seconds: Optional[int] = None
    break_60_remaining_seconds: Optional[int] = None


class LiveSeriesPoint(BaseModel):
    interval_start: datetime
    active_calls: float
    on_hold: float


class PredictionOut(BaseModel):
    interval_start: datetime
    predicted_call_volume: float
    predicted_aht: float
    required_agents_net: float
    required_agents_gross: float
    traffic_intensity: float
    achieved_sla: float


class WeeklyPlanningDay(BaseModel):
    date: str
    day_name: str
    total_call_volume: int
    required_agents_net_peak: int
    required_agents_gross_peak: int
    target_sla: float
    shrinkage: float


# ------------------------------------------------------------------
# API Routes
# ------------------------------------------------------------------
@app.get("/api/v1/live/kpis", response_model=LiveKPIOut)
async def get_live_kpis():
    try:
        async with async_session_factory() as session:
            now = datetime.now(timezone.utc)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

            total_calls = await session.scalar(
                select(func.sum(HistoricalFlux.call_volume))
                .where(HistoricalFlux.interval_start >= start_of_day)
            ) or 0

            avg_aht = await session.scalar(
                select(func.avg(HistoricalFlux.aht_seconds))
                .where(HistoricalFlux.interval_start >= start_of_day)
            ) or 300.0
            avg_talk_str = f"{int(avg_aht // 60)}:{int(avg_aht % 60):02d}"

            last_flux = (await session.execute(
                select(HistoricalFlux)
                .order_by(HistoricalFlux.interval_start.desc())
                .limit(1)
            )).scalars().first()

            if last_flux:
                recent_calls = last_flux.call_volume
                recent_aht = last_flux.aht_seconds
                agents_present = last_flux.agents_present
            else:
                recent_calls = 0
                recent_aht = 300
                agents_present = 0

            active_now = max(0, recent_calls // 2 + random.randint(-3, 5))
            waiting_now = max(0, int(active_now * random.uniform(0.1, 0.3)))
            longest_wait = random.randint(30, 120)
            longest_str = f"{longest_wait // 60:02d}:{longest_wait % 60:02d}"
            asa = random.randint(20, 60)
            abandoned = random.randint(0, 8)

            agent_logged = agents_present + random.randint(0, 3)
            agent_ready = max(0, agent_logged - active_now // 3)

            gross, net, traffic, sla = erlang_c_staffing(
                call_volume=active_now,
                aht_seconds=recent_aht,
                interval_minutes=15,
                target_answer_time=20,
                target_sla=0.80,
            )
            service_level_pct = round(sla * 100, 1)
            occupancy = (traffic / agent_logged * 100) if agent_logged > 0 else 0.0

            alerts = []
            if occupancy < 65:
                alerts.append("Sous‑occupation")
            elif occupancy > 85:
                alerts.append("Sur‑occupation / Burnout")
            if waiting_now > 10:
                alerts.append(f"File d’attente élevée ({waiting_now})")

            return LiveKPIOut(
                longest_call_waiting=longest_str,
                current_call_waiting=waiting_now,
                average_talk_time=avg_talk_str,
                total_calls_today=int(total_calls),
                agent_ready=agent_ready,
                agent_logged_in=agent_logged,
                asa_seconds=asa,
                abandoned_today=abandoned,
                occupancy_pct=round(occupancy, 1),
                service_level_pct=service_level_pct,
                alerts=alerts,
            )
    except Exception:
        logger.exception("Live KPI fetch failed.")
        raise HTTPException(status_code=500, detail="Internal server error.")


@app.get("/api/v1/live/agents", response_model=LiveAgentOut)
async def get_live_agents():
    try:
        async with async_session_factory() as session:
            last_staff = (await session.execute(
                select(AgentStaffing)
                .order_by(AgentStaffing.interval_start.desc())
                .limit(1)
            )).scalars().first()

            if not last_staff:
                return LiveAgentOut(
                    agents_actual=0,
                    agents_scheduled=0,
                    agents_on_break_15=0,
                    agents_on_break_60=0,
                    agents_over_aht=0,
                    agents_late=0,
                    agents_finished_shift=0,
                )

            now = datetime.now(timezone.utc)
            break_15_remaining = None
            if last_staff.break_15_return_time and last_staff.agents_on_break_15 > 0:
                delta = (last_staff.break_15_return_time - now).total_seconds()
                break_15_remaining = max(0, int(delta))

            break_60_remaining = None
            if last_staff.break_60_return_time and last_staff.agents_on_break_60 > 0:
                delta = (last_staff.break_60_return_time - now).total_seconds()
                break_60_remaining = max(0, int(delta))

            return LiveAgentOut(
                agents_actual=last_staff.agents_actual,
                agents_scheduled=last_staff.agents_scheduled,
                agents_on_break_15=last_staff.agents_on_break_15,
                agents_on_break_60=last_staff.agents_on_break_60,
                agents_over_aht=last_staff.agents_over_aht,
                agents_late=last_staff.agents_late,
                agents_finished_shift=last_staff.agents_finished_shift,
                break_15_remaining_seconds=break_15_remaining,
                break_60_remaining_seconds=break_60_remaining,
            )
    except Exception:
        logger.exception("Live agents fetch failed.")
        raise HTTPException(status_code=500, detail="Internal server error.")


@app.get("/api/v1/live/series", response_model=List[LiveSeriesPoint])
async def get_live_series():
    try:
        async with async_session_factory() as session:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=60)
            stmt = (
                select(HistoricalFlux)
                .where(HistoricalFlux.interval_start >= cutoff)
                .order_by(HistoricalFlux.interval_start)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            series = []
            for r in rows:
                active = r.call_volume // 2 + random.randint(-2, 5)
                on_hold = max(0, int(active * random.uniform(0.1, 0.3)))
                series.append(LiveSeriesPoint(
                    interval_start=r.interval_start,
                    active_calls=active,
                    on_hold=on_hold,
                ))
            return series
    except Exception:
        logger.exception("Live series fetch failed.")
        raise HTTPException(status_code=500, detail="Internal server error.")


# Nouvelles routes de prévisions
@app.get("/api/v1/predict/today", response_model=List[PredictionOut])
async def get_today_predictions():
    """Return today's detailed 15-min predictions with staffing."""
    try:
        async with async_session_factory() as session:
            now = datetime.now(timezone.utc)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)

            stmt = (
                select(PredictionsTactical)
                .where(
                    PredictionsTactical.interval_start >= start_of_day,
                    PredictionsTactical.interval_start < end_of_day,
                )
                .order_by(PredictionsTactical.interval_start)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

            output = []
            for row in rows:
                gross, net, traffic, sla = erlang_c_staffing(
                    call_volume=row.predicted_call_volume,
                    aht_seconds=row.predicted_aht,
                )
                output.append(
                    PredictionOut(
                        interval_start=row.interval_start,
                        predicted_call_volume=row.predicted_call_volume,
                        predicted_aht=row.predicted_aht,
                        required_agents_net=net,
                        required_agents_gross=gross,
                        traffic_intensity=traffic,
                        achieved_sla=sla,
                    )
                )
            return output
    except Exception:
        logger.exception("Failed to fetch today predictions.")
        raise HTTPException(status_code=500, detail="Internal server error.")


@app.get("/api/v1/predict/week", response_model=List[WeeklyPlanningDay])
async def get_weekly_planning():
    """
    Return aggregated daily predictions for the next 7 days,
    with recommended staffing (peak agents net/gross).
    """
    try:
        async with async_session_factory() as session:
            now = datetime.now(timezone.utc)
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)

            stmt = (
                select(PredictionsTactical)
                .where(
                    PredictionsTactical.interval_start >= start,
                    PredictionsTactical.interval_start < end,
                )
                .order_by(PredictionsTactical.interval_start)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

            if not rows:
                logger.warning("No weekly predictions found, generating now...")
                await run_forecast_pipeline()
                result = await session.execute(stmt)
                rows = result.scalars().all()

            days = defaultdict(list)
            for row in rows:
                day_key = row.interval_start.strftime("%Y-%m-%d")
                days[day_key].append(row)

            planning = []
            for i in range(7):
                day_date = start + timedelta(days=i)
                day_key = day_date.strftime("%Y-%m-%d")
                day_rows = days.get(day_key, [])

                if not day_rows:
                    planning.append(WeeklyPlanningDay(
                        date=day_key,
                        day_name=day_date.strftime("%A"),
                        total_call_volume=0,
                        required_agents_net_peak=0,
                        required_agents_gross_peak=0,
                        target_sla=80.0,
                        shrinkage=17.65,
                    ))
                    continue

                total_calls = sum(r.predicted_call_volume for r in day_rows)
                peak_net = 0
                peak_gross = 0
                target_sla = 0.80
                shrinkage = 0.1765
                for r in day_rows:
                    gross, net, traffic, sla = erlang_c_staffing(
                        call_volume=r.predicted_call_volume,
                        aht_seconds=r.predicted_aht,
                        target_sla=target_sla,
                        shrinkage=shrinkage,
                    )
                    if net > peak_net:
                        peak_net = int(math.ceil(net))
                        peak_gross = int(math.ceil(gross))
                        # le sla obtenu est le même pour chaque intervalle, on garde le dernier

                planning.append(WeeklyPlanningDay(
                    date=day_key,
                    day_name=day_date.strftime("%A"),
                    total_call_volume=int(total_calls),
                    required_agents_net_peak=peak_net,
                    required_agents_gross_peak=peak_gross,
                    target_sla=target_sla * 100,
                    shrinkage=shrinkage * 100,
                ))

            return planning
    except Exception:
        logger.exception("Weekly planning fetch failed.")
        raise HTTPException(status_code=500, detail="Internal server error.")