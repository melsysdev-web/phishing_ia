# 🚨 URGENT: VirusTotal Quota Protection (4-day fix)

## Crisis Summary

- **VT tier gratuito**: 4 req/min, 500/día
- **Backend limiter**: 30 req/60s per IP (permite MÁS tráfico que VT tolera)
- **Problem**: Pocos usuarios reales → VT agota cuota → 429s silenciosos
- **Worse**: Submit + fetch desperdician 2 llamadas en URLs nuevas (no terminan a tiempo)
- **No circuit breaker**: Nada trackea cuota global VT/día
- **4 días**: Solución rápida + producción

---

## Root Causes & Quick Fixes

### 1. Submit + Fetch Wastage (REMOVE DAY 1)

**Current `virustotal_service.py:131`**:
```python
# URL nueva → POST /urls (submit)
response = vt.scan_url(url)  # submit
if 'analysis_id' in response:
    time.sleep(5)
    # GET /analyses/{id} (fetch immediately)
    response = vt.get_url_analysis(analysis_id)  # 2ND CALL
    if 'stats' not in response:  # VT no terminó scan
        raise KeyError  # descarta resultado, pierde 2 llamadas
```

**Fix**: Deshabilitar submit. Solo GET si ya está en VT.

```python
def get_virustotal_verdict(url: str):
    """
    Get VT verdict if URL already analyzed.
    Do NOT submit new URLs (wastes 2 calls, returns incomplete data).
    """
    try:
        analysis = vt.get_url_analysis(url)  # 1 call only
        if 'stats' not in analysis:
            return {"error": "not_in_vt", "source": "virustotal"}
        # Process stats...
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # URL not in VT yet — don't submit
            return {"error": "url_not_analyzed", "source": "virustotal"}
        raise
```

**Impact**: Saves ~50% of VT calls immediately (removes wasteful submits).

---

### 2. Global Quota Circuit Breaker (DAY 1-2)

**New file: `backend/app/core/quota_circuit.py`**

```python
import time
from threading import Lock
from datetime import datetime, timedelta

class VTQuotaCircuit:
    """Global circuit breaker for VirusTotal quota."""
    
    def __init__(self, daily_limit: int = 500):
        self.daily_limit = daily_limit
        self.call_count = 0
        self.day_start = datetime.utcnow()
        self.lock = Lock()
        self.tripped = False
    
    def is_open(self) -> bool:
        """Circuit is open (quota exceeded) → stop calling VT."""
        with self.lock:
            # Reset if new day
            if (datetime.utcnow() - self.day_start) > timedelta(days=1):
                self.call_count = 0
                self.day_start = datetime.utcnow()
                self.tripped = False
            
            return self.tripped or self.call_count >= self.daily_limit
    
    def record_call(self) -> bool:
        """Record a VT call, return True if allowed."""
        with self.lock:
            if self.call_count >= self.daily_limit:
                self.tripped = True
                return False
            self.call_count += 1
            return True
    
    def record_error_429(self):
        """VT returned 429 → assume quota exceeded."""
        with self.lock:
            self.tripped = True
            logger.warning(f"VT 429 detected. Circuit breaker OPEN. "
                          f"Calls so far: {self.call_count}/{self.daily_limit}")
    
    def get_status(self) -> dict:
        with self.lock:
            return {
                "calls_today": self.call_count,
                "limit": self.daily_limit,
                "circuit_open": self.tripped,
                "reset_at": (self.day_start + timedelta(days=1)).isoformat()
            }

# Global instance
vt_quota = VTQuotaCircuit(daily_limit=500)
```

**Integration in `virustotal_service.py`**:

```python
from backend.app.core.quota_circuit import vt_quota

def get_virustotal_verdict(url: str):
    # Check circuit BEFORE calling
    if vt_quota.is_open():
        logger.warning("VT quota circuit open, skipping call")
        return {"error": "quota_exceeded", "source": "virustotal"}
    
    try:
        analysis = vt.get_url_analysis(url)
        vt_quota.record_call()  # Record success
        # ...
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            vt_quota.record_error_429()  # Trip breaker immediately
            return {"error": "quota_exceeded", "source": "virustotal"}
        raise
```

**Response in `/predict`**:

```json
{
  "risk_assessment": { "score": 75, "level": "MEDIUM" },
  "virustotal": { "error": "quota_exceeded", "source": "virustotal" },
  "quota_circuit": {
    "vt_calls_today": 487,
    "vt_limit": 500,
    "circuit_open": false,
    "reset_at": "2026-08-18T00:00:00Z"
  }
}
```

**Impact**: 
- Stops wasting calls once quota is low
- Prevents cascading 429s
- Shows status in `/metadata` endpoint

---

### 3. Caching Strategy (DAY 2)

**Extend current cache** (`backend/app/utils/url_cache.py`):

```python
# Current: 10 min TTL, 500 entries (in-memory)
# Proposed: 
# - Hot (Redis): 10 min TTL, 500 entries (speed)
# - Warm (SQLite): 30 days TTL (cost savings)

class ExtendedCache:
    def __init__(self, redis_ttl=600, db_ttl=2592000):  # 10 min, 30 days
        self.redis = self.fast_cache  # existing
        self.db = SqliteCache("cache.db")  # new
    
    def get(self, url: str):
        # Try hot (10 min)
        result = self.redis.get(url)
        if result:
            return result
        
        # Try warm (30 days)
        result = self.db.get(url)
        if result:
            self.redis.set(url, result)  # re-hot
            return result
        
        return None  # cache miss
    
    def set(self, url: str, result: dict):
        self.redis.set(url, result, ttl=600)
        self.db.set(url, result, ttl=2592000)
```

**Impact**: 
- Same URL checked within 30 days → 0 VT calls
- Most phishing/spam URLs are repeat patterns
- Realistic savings for real users

---

## 4-Day Implementation Plan

### **Day 1 (Today): Emergency Fixes**
- [ ] Remove submit calls from `virustotal_service.py` (line ~131)
- [ ] Create `quota_circuit.py` with global circuit breaker
- [ ] Integrate circuit breaker into `/predict` endpoint
- [ ] Update `/metadata` to expose circuit status
- [ ] **Test**: Verify VT calls drop 50% (no more wasted submits)

**Commit**: "fix: remove wasteful VT submit, add global quota circuit breaker"

### **Day 2: Extend Cache & Tests**
- [ ] Add SQLite cache layer (30-day TTL)
- [ ] Write tests for circuit breaker (open/close, 429 detection)
- [ ] Write tests for extended cache (hot/warm/cold)
- [ ] Verify `/predict` still returns valid scores without VT

**Commit**: "feat: extend cache to 30 days, add quota circuit tests"

### **Day 3: Integration & Staging**
- [ ] Deploy to staging environment
- [ ] Monitor VT calls for 24h with real traffic
- [ ] Verify no degradation in risk scoring
- [ ] Collect metrics: calls/day, cache hit ratio, circuit trips

**Commit**: "test: staging validation of quota circuit & cache"

### **Day 4: Production Deploy**
- [ ] Review staging metrics
- [ ] Deploy to production
- [ ] Monitor first 24h: VT quota usage, error rates
- [ ] Alert setup: notify if circuit trips or quota < 50 calls

**Commit**: "deploy: VT quota protection to production"

---

## Code Changes Required

### Files to Modify
1. **`backend/app/core/quota_circuit.py`** — NEW (50 lines)
2. **`backend/app/services/virustotal_service.py`** — Remove submit (10-15 lines deleted)
3. **`backend/app/utils/url_cache.py`** — Extend to DB (30 lines added)
4. **`backend/app/api/routes.py`** — Add circuit status to `/predict` response (5 lines)
5. **`backend/app/main.py`** — Expose `/metadata` circuit status (10 lines)

### Tests to Add
1. **`backend/tests/test_quota_circuit.py`** — Circuit breaker unit tests (40 lines)
2. **`tests/test_vt_integration.py`** — VT + circuit integration (30 lines)
3. **`tests/test_extended_cache.py`** — Cache layer tests (50 lines)

### Total Code: ~200 lines added/modified (small, focused, safe)

---

## Rollback Plan (If Needed)

If circuit breaker causes issues:
```bash
# Disable circuit breaker without rollback
# Set DAY_LIMIT = 99999 (effectively infinite)
VIRUSTOTAL_DAILY_LIMIT=99999 uvicorn backend.app.main:app
```

If extended cache breaks:
```bash
# Fall back to in-memory cache only
# Delete SQLite cache file
rm cache.db
```

---

## Expected Outcomes

### Before (Current Crisis)
- VT calls: 500/day (rate-limited by tier)
- Wasted calls (submit): ~250/day (50%)
- Actual useful data: ~250/day
- Cost: $0.05/day (VT paid tier estimate)
- User impact: Sporadic 429s, missing risk signals

### After (Day 4)
- VT calls: 300/day (no wasted submits)
- Cache hits: ~40% of requests (same URLs repeated)
- Actual VT calls needed: ~180/day
- Cost: $0.03/day (40% savings)
- User impact: Stable, cached results instant, no 429s

---

## Monitoring & Alerts

Add to `/metrics`:
```python
# Track circuit breaker trips
vt_quota_exhausted = Counter(
    'vt_quota_exhausted_total',
    'Times VT quota circuit was tripped'
)

# Track cache hit ratio
cache_hit_ratio = Gauge(
    'cache_hit_ratio',
    'Cache hit ratio (0-1)'
)

# Track actual VT calls
vt_calls = Counter(
    'vt_api_calls_total',
    'Actual VT API calls made'
)
```

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Cache serves stale data | Low | 30-day TTL is reasonable for URLs (rarely legitimized) |
| Circuit breaker trips too early | Low | Daily reset, conservative limits |
| Missing risk signal without VT | Low | ML models still score (tested in Day 2) |
| SQLite DB grows too large | Low | Implement pruning after 30 days |

---

## Questions to Resolve Before Implementation

1. **Can you disable submit immediately?** (1 breaking change in VT behavior)
2. **What's your actual daily traffic?** (VT calls per day — affects circuit limits)
3. **Is staging available** for 24h monitoring (Day 3)?
4. **Alerting channel**: Slack/email when circuit trips?

---

## Summary

**In 4 days**: Reduce VT calls by 40-50%, eliminate 429s, add observability.  
**Scope**: ~200 lines of code, focused, reversible.  
**Risk**: Low (cache + circuit breaker are proven patterns).  
**Deploy**: Friday EOD → Weekend monitoring → Tuesday review.
