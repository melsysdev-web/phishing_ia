"""Tests para backend/app/core/quota_circuit.py — circuit breaker global."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from backend.app.core.quota_circuit import ApiQuotaCircuit


class TestApiQuotaCircuit:
    """Tests para circuit breaker de cuota API."""

    def test_init_defaults(self):
        circuit = ApiQuotaCircuit(daily_limit=100, api_name="TestAPI")
        assert circuit.daily_limit == 100
        assert circuit.call_count == 0
        assert circuit.tripped is False

    def test_is_open_returns_false_when_under_limit(self):
        circuit = ApiQuotaCircuit(daily_limit=10)
        circuit.call_count = 5
        assert circuit.is_open() is False

    def test_is_open_returns_true_when_at_limit(self):
        circuit = ApiQuotaCircuit(daily_limit=10)
        circuit.call_count = 10
        assert circuit.is_open() is True

    def test_is_open_returns_true_when_tripped(self):
        circuit = ApiQuotaCircuit(daily_limit=100)
        circuit.tripped = True
        assert circuit.is_open() is True

    def test_record_call_increments_count(self):
        circuit = ApiQuotaCircuit(daily_limit=10)
        result = circuit.record_call()
        assert result is True
        assert circuit.call_count == 1

    def test_record_call_returns_false_at_limit(self):
        circuit = ApiQuotaCircuit(daily_limit=3)
        circuit.record_call()
        circuit.record_call()
        circuit.record_call()
        result = circuit.record_call()
        assert result is False

    def test_record_call_trips_circuit_at_limit(self):
        circuit = ApiQuotaCircuit(daily_limit=2)
        circuit.record_call()
        circuit.record_call()
        circuit.record_call()
        assert circuit.tripped is True

    def test_record_error_429_trips_circuit(self):
        circuit = ApiQuotaCircuit(daily_limit=100)
        circuit.call_count = 50
        circuit.record_error_429()
        assert circuit.tripped is True
        assert circuit.trip_reason == "http_429_received"

    def test_get_status_returns_dict(self):
        circuit = ApiQuotaCircuit(daily_limit=100)
        circuit.call_count = 40
        status = circuit.get_status()
        assert isinstance(status, dict)
        assert status["calls_today"] == 40
        assert status["limit"] == 100
        assert status["remaining"] == 60
        assert status["circuit_open"] is False

    def test_get_status_when_circuit_open(self):
        circuit = ApiQuotaCircuit(daily_limit=100)
        circuit.tripped = True
        circuit.trip_reason = "quota_exceeded"
        status = circuit.get_status()
        assert status["circuit_open"] is True
        assert status["trip_reason"] == "quota_exceeded"

    def test_reset_if_new_day_clears_counters(self):
        circuit = ApiQuotaCircuit(daily_limit=100)
        circuit.call_count = 50
        circuit.tripped = True
        circuit.day_start = datetime.now(timezone.utc) - timedelta(days=2)

        circuit.reset_if_new_day()

        assert circuit.call_count == 0
        assert circuit.tripped is False

    def test_manual_trip(self):
        circuit = ApiQuotaCircuit(daily_limit=100)
        circuit.manual_trip(reason="persistent_errors")
        assert circuit.tripped is True
        assert circuit.trip_reason == "persistent_errors"

    def test_concurrent_record_calls_thread_safe(self):
        import threading

        circuit = ApiQuotaCircuit(daily_limit=1000)

        def record_calls(n):
            for _ in range(n):
                circuit.record_call()

        threads = [
            threading.Thread(target=record_calls, args=(100,))
            for _ in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert circuit.call_count == 500

    def test_remaining_is_zero_when_at_limit(self):
        circuit = ApiQuotaCircuit(daily_limit=10)
        circuit.call_count = 10
        status = circuit.get_status()
        assert status["remaining"] == 0

    def test_remaining_never_negative(self):
        circuit = ApiQuotaCircuit(daily_limit=10)
        circuit.call_count = 15
        status = circuit.get_status()
        assert status["remaining"] == 0
