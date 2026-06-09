"""
Pure-Python implementation of the Erlang-C formula for WFM staffing.
No heavy dependencies – only the standard library math module.
AHT is capped at 420 seconds (7 minutes).
"""

import math
from typing import Tuple

INTERVAL_SECONDS = 15 * 60  # 900 s
AHT_CAP = 420  # seconds
SHRINKAGE = 0.1765  # 17.65%


def _erlang_c_probability(
    traffic_intensity: float, agents: int
) -> float:
    if agents <= 0:
        return 1.0
    if traffic_intensity <= 0:
        return 0.0
    if agents <= traffic_intensity:
        return 1.0

    sum_terms = 0.0
    fact_k = 1
    for k in range(agents):
        if k > 0:
            fact_k *= k
        sum_terms += (traffic_intensity ** k) / fact_k

    fact_agents = fact_k * agents
    term_agents = (traffic_intensity ** agents) / fact_agents

    denominator = sum_terms + term_agents * (agents / (agents - traffic_intensity))
    if denominator == 0:
        return 0.0

    prob = term_agents * (agents / (agents - traffic_intensity)) / denominator
    return prob


def _average_speed_of_answer(
    traffic_intensity: float, agents: int, avg_handling_time: float
) -> float:
    p_w = _erlang_c_probability(traffic_intensity, agents)
    if agents <= traffic_intensity:
        return float("inf")
    return (p_w * avg_handling_time) / (agents - traffic_intensity)


def _service_level(
    traffic_intensity: float, agents: int, target_answer_time: float, avg_handling_time: float
) -> float:
    p_w = _erlang_c_probability(traffic_intensity, agents)
    if agents <= traffic_intensity:
        return 0.0
    exponent = -(agents - traffic_intensity) * target_answer_time / avg_handling_time
    return 1 - p_w * math.exp(exponent)


def erlang_c_staffing(
    call_volume: float,
    aht_seconds: float,
    interval_minutes: int = 15,
    target_answer_time: float = 20.0,
    target_sla: float = 0.80,
    shrinkage: float = SHRINKAGE,
) -> Tuple[float, float, float, float]:
    if call_volume <= 0:
        return 0.0, 0.0, 0.0, 1.0

    aht = min(aht_seconds, AHT_CAP)
    interval_seconds = interval_minutes * 60.0
    traffic = (call_volume * aht) / interval_seconds

    if traffic <= 0:
        return 0.0, 0.0, 0.0, 1.0

    agents = max(1, math.floor(traffic))
    while True:
        sla = _service_level(traffic, agents, target_answer_time, aht)
        if sla >= target_sla:
            break
        agents += 1
        if agents > 10000:
            break

    gross = float(agents)
    net = gross / (1.0 - shrinkage) if shrinkage < 1.0 else gross

    return gross, net, traffic, sla