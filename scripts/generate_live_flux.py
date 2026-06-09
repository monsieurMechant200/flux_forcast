#!/usr/bin/env python3
"""
CLI wrapper for the live data simulator.
Usage: python scripts/generate_live_flux.py [scenario]
"""

import asyncio
import sys
from app.services.simulator import inject_scenario
from app.models.database import init_db


async def main(scenario: str):
    await init_db()
    records = await inject_scenario(scenario)
    print(
        f"Scenario '{scenario}' injected: {len(records)} intervals "
        f"(volumes: {[r.call_volume for r in records]})."
    )


if __name__ == "__main__":
    scenario = sys.argv[1] if len(sys.argv) > 1 else "standard"
    asyncio.run(main(scenario))