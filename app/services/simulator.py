"""
Simulated live data injector – reusable by both the CLI script and the API.
"""
import random
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

from app.models.database import async_session_factory
from app.models.domain import HistoricalFlux, AgentStaffing

SCENARIO_PARAMS = {
    "standard": {"volume_scale": 1.0, "aht_scale": 1.0, "agents_scale": 1.0},
    "crise_reseau": {"volume_scale": 1.8, "aht_scale": 1.4, "agents_scale": 0.9},
    "sous_effectif": {"volume_scale": 1.0, "aht_scale": 1.0, "agents_scale": 0.7},
}

def _generate_intervals(now: datetime, scenario_params: dict) -> List[Tuple[datetime, int, float, int]]:
    intervals = []
    for i in reversed(range(2)):
        start = now - timedelta(minutes=15 * (i + 1))
        base_volume = random.randint(50, 80)
        volume = max(0, int(base_volume * scenario_params["volume_scale"]))
        base_aht = random.uniform(250, 350)
        aht = min(420.0, base_aht * scenario_params["aht_scale"])
        base_agents = max(1, int(volume / 12 + random.randint(-2, 2)))
        agents = max(1, int(base_agents * scenario_params["agents_scale"]))
        intervals.append((start, volume, aht, agents))
    return intervals

async def inject_scenario(scenario_name: str = "standard") -> List[HistoricalFlux]:
    params = SCENARIO_PARAMS.get(scenario_name, SCENARIO_PARAMS["standard"])
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    data = _generate_intervals(now, params)

    async with async_session_factory() as session:
        records = []
        for start, vol, aht, agents in data:
            on_break_15 = random.randint(0, max(1, agents // 5))
            on_break_60 = random.randint(0, max(1, agents // 8))
            over_aht = random.randint(0, max(1, agents // 10))
            late = random.randint(0, max(1, agents // 10))
            finished = random.randint(0, max(1, agents // 6))

            break_15_return = start + timedelta(minutes=15) if on_break_15 > 0 else None
            break_60_return = start + timedelta(minutes=60) if on_break_60 > 0 else None

            hist = HistoricalFlux(
                interval_start=start,
                call_volume=vol,
                aht_seconds=aht,
                agents_present=agents,
            )
            staff = AgentStaffing(
                interval_start=start,
                agents_scheduled=agents + random.randint(0, 2),
                agents_actual=agents,
                agents_on_break_15=on_break_15,
                agents_on_break_60=on_break_60,
                agents_over_aht=over_aht,
                agents_late=late,
                agents_finished_shift=finished,
                break_15_return_time=break_15_return,
                break_60_return_time=break_60_return,
            )
            session.add_all([hist, staff])
            records.append(hist)
        await session.commit()
    return records