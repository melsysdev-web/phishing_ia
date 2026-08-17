"""
Global circuit breaker for expensive API calls (VirusTotal, Safe Browsing).

Tracks daily call counts and trips circuit when quota is exceeded.
Prevents cascading failures and alerts operators before quota exhaustion.
"""

import logging
from datetime import datetime, timedelta
from threading import Lock

logger = logging.getLogger(__name__)


class ApiQuotaCircuit:
    """Circuit breaker for API quota tracking."""

    def __init__(self, daily_limit: int = 500, api_name: str = "API"):
        self.daily_limit = daily_limit
        self.api_name = api_name
        self.call_count = 0
        self.day_start = datetime.utcnow()
        self.lock = Lock()
        self.tripped = False
        self.trip_reason = None

    def reset_if_new_day(self):
        """Reset counters if day has changed."""
        if (datetime.utcnow() - self.day_start) >= timedelta(days=1):
            with self.lock:
                self.call_count = 0
                self.day_start = datetime.utcnow()
                self.tripped = False
                self.trip_reason = None
                logger.info(f"{self.api_name} quota reset for new day")

    def is_open(self) -> bool:
        """Return True if circuit is open (quota exceeded or tripped)."""
        self.reset_if_new_day()
        with self.lock:
            return self.tripped or self.call_count >= self.daily_limit

    def record_call(self) -> bool:
        """
        Record a successful API call.
        Return True if call was allowed, False if quota exceeded.
        """
        self.reset_if_new_day()
        with self.lock:
            if self.call_count >= self.daily_limit:
                self.tripped = True
                self.trip_reason = "quota_exceeded"
                return False
            self.call_count += 1
            return True

    def record_error_429(self):
        """
        API returned 429 (rate limited).
        Assume quota is exhausted and trip circuit.
        """
        with self.lock:
            self.tripped = True
            self.trip_reason = "http_429_received"
            logger.warning(
                f"{self.api_name} returned 429. Circuit OPEN. "
                f"Calls so far: {self.call_count}/{self.daily_limit}"
            )

    def get_status(self) -> dict:
        """Return current circuit status."""
        self.reset_if_new_day()
        with self.lock:
            reset_time = self.day_start + timedelta(days=1)
            return {
                "calls_today": self.call_count,
                "limit": self.daily_limit,
                "remaining": max(0, self.daily_limit - self.call_count),
                "circuit_open": self.tripped,
                "trip_reason": self.trip_reason,
                "reset_at": reset_time.isoformat() + "Z",
            }

    def manual_trip(self, reason: str = "manual"):
        """Manually trip the circuit (e.g., after receiving persistent errors)."""
        with self.lock:
            self.tripped = True
            self.trip_reason = reason
            logger.warning(f"{self.api_name} circuit manually tripped: {reason}")


# Global instances for each expensive API
vt_quota = ApiQuotaCircuit(daily_limit=500, api_name="VirusTotal")
safe_browsing_quota = ApiQuotaCircuit(daily_limit=10000, api_name="SafeBrowsing")
fact_check_quota = ApiQuotaCircuit(daily_limit=1000, api_name="FactCheck")
