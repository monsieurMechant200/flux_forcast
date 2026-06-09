"""
Strict mathematical tests for Erlang-C engine.
"""
import math
import pytest
from app.services.erlang_c import (
    erlang_c_staffing,
    _erlang_c_probability,
    _service_level,
    INTERVAL_SECONDS,
    AHT_CAP,
    SHRINKAGE,
)


def test_erlang_c_probability_known():
    p = _erlang_c_probability(5.0, 6)
    assert p > 0.0
    assert p < 1.0


def test_erlang_c_probability_zero_traffic():
    assert _erlang_c_probability(0.0, 1) == 0.0


def test_erlang_c_probability_agents_equal_traffic():
    assert _erlang_c_probability(2.0, 2) == 1.0


def test_service_level_perfect():
    # Avec 50 agents pour 1 Erlang, SLA ≈ 1
    sla = _service_level(1.0, 50, 20, 300)
    assert sla == pytest.approx(1.0, abs=1e-6)


def test_service_level_zero():
    sla = _service_level(5.0, 5, 20, 300)
    assert sla == 0.0


def test_erlang_c_staffing_standard():
    gross, net, traffic, sla = erlang_c_staffing(100, 300, 15, 20, 0.80)
    assert gross > 0
    assert net > gross
    assert 0.79 < sla <= 1.0


def test_erlang_c_staffing_zero_volume():
    gross, net, traffic, sla = erlang_c_staffing(0, 300)
    assert gross == 0.0
    assert net == 0.0
    assert sla == 1.0


def test_aht_capping():
    gross, net, traffic, sla = erlang_c_staffing(10, 800, 15)
    expected_traffic = (10 * 420) / INTERVAL_SECONDS
    assert math.isclose(traffic, expected_traffic, rel_tol=1e-9)


def test_shrinkage_multiplier():
    gross, net, _, _ = erlang_c_staffing(120, 320, 15, 20, 0.80, shrinkage=0.2)
    expected_net = gross / (1 - 0.2)
    assert math.isclose(net, expected_net, rel_tol=1e-9)