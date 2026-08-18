# 🚀 Redis Caching Strategy

**Purpose**: High-performance distributed cache layer  
**Tier**: L0 (fastest) → L1 (warm) → L2 (compute)

---

## The Problem (Current State)

### Current Cache Architecture

```
Request
  ↓
┌─────────────────────────────────┐
│   In-Memory Cache (FastAPI)     │ ← 10 min TTL, 500 entries
│   • 1-5 ms response time        │
│   • Only on 1 instance          │   ❌ NOT distributed
│   • Lost on restart             │   ❌ Lost on deploy
└─────────────────────────────────┘
  ↓ Cache Miss
┌─────────────────────────────────┐
│   SQLite Warm Cache             │ ← 30 day TTL
│   • 10-50 ms response time      │
│   • Persistent                  │
│   • No concurrency support      │   ❌ Slower than needed
└─────────────────────────────────┘
  ↓ Cache Miss
┌─────────────────────────────────┐
│   Full Analysis Pipeline        │ ← 3-5 seconds
│   • URL features                │   ❌ Expensive!
│   • HTML fetch                  │
│   • ML models (RF + RoBERTa)    │
│   • External APIs (VT, SB, FC)  │
└─────────────────────────────────┘
```

### Current Performance Impact

| Scenario | Latency | Cost (API calls) |
|----------|---------|------------------|
| Cache hit (memory) | 5ms | 0 |
| Cache hit (SQLite) | 50ms | 0 |
| **Cache miss** | **3-5s** | **3-4 calls** 💰 |

**Problem**: 
- Multiple backends can't share cache
- On deploy: cache lost, cold start for 5-10 min
- At scale: each server duplicates computations

---

## The Solution: Redis L0 Layer

### New Architecture

```
Request
  ↓
┌─────────────────────────────────────────┐
│   Redis Cache (L0 - SUPER FAST)        │ ← 10 min TTL
│   • <1 ms response time                 │
│   • Distributed across servers          │   ✅ Shared!
│   • In-memory, extremely fast           │   ✅ Fast!
│   • Survived restarts (persistence)     │   ✅ Persistent!
└─────────────────────────────────────────┘
  ↓ Cache Miss
┌─────────────────────────────────────────┐
│   SQLite Cache (L1 - WARM LAYER)        │ ← 30 day TTL
│   • 10-50 ms response time              │
│   • Persistent storage                  │
└─────────────────────────────────────────┘
  ↓ Cache Miss
┌─────────────────────────────────────────┐
│   Full Analysis Pipeline (L2)           │ ← 3-5 seconds
│   • Only when truly new URL             │   ✅ Rare!
└─────────────────────────────────────────┘
```

---

## Benefits of Redis

### 1. **Speed** ⚡

| Cache | Response Time | Improvement |
|-------|---|---|
| Memory (current) | 1-5 ms | baseline |
| **Redis** | **<1 ms** | **2-5x faster** |
| SQLite | 10-50 ms | 10-50x slower |
| Compute | 3-5 s | 3000-5000x slower |

**Impact**: 
- User sees results instantly
- 95th percentile latency: 5-7ms (vs 50-100ms)

### 2. **Distribution** 🔄

**Current**: Each server has own cache (duplicated work)

```
User A → Server 1 → Cache 1 → Compute [3s]
User B → Server 2 → Cache 2 → Compute [3s]  ❌ Both compute same URL!

With Redis → Server 1 → Cache 2 → Hit [<1ms] ✅ Shared!
```

**Benefits**:
- Reduced API calls to external services
- Better cost efficiency
- Lower infrastructure load

### 3. **Availability** 🛡️

**Current**: 
- Deploy → In-memory cache cleared
- Fresh start → All URLs trigger full analysis
- 5-10 min to warm up

**With Redis**:
- Deploy → Redis persists
- Instant cache restoration
- No cold start penalty

### 4. **Scalability** 📈

Can handle:
- Multiple backend instances
- High concurrent requests
- Growing cache size (up to Redis limits)

---

## Redis in the Architecture

### Deployment

```
Render Web Service (3 instances)
    ↓ All connect to
┌─────────────────────────────┐
│   Redis Cache Service       │
│   • Shared across instances │
│   • Fast in-memory DB       │
│   • Persistence enabled     │
└─────────────────────────────┘
    ↓ Fallback if Redis down
┌─────────────────────────────┐
│   SQLite on local disk      │
│   • Graceful degradation    │
│   • Always available        │
└─────────────────────────────┘
```

### Configuration

```python
class CacheManager:
    """Three-tier cache hierarchy."""
    
    def __init__(self, redis_url=None, db_path=None):
        self.redis = redis.from_url(redis_url) if redis_url else None
        self.sqlite = SqliteCache(db_path)
        
    def get(self, url):
        # Try L0: Redis (<1ms)
        if self.redis:
            result = self.redis.get(url)
            if result:
                return json.loads(result)
        
        # Try L1: SQLite (10-50ms)
        result = self.sqlite.get(url)
        if result:
            # Restore to Redis for next user
            if self.redis:
                self.redis.setex(url, 600, json.dumps(result))
            return result
        
        # Cache miss → compute
        return None
    
    def set(self, url, data):
        # Write to both L0 and L1
        if self.redis:
            self.redis.setex(url, 600, json.dumps(data))  # 10 min
        self.sqlite.set(url, data, ttl=2592000)  # 30 days
```

---

## Real-World Impact

### Before Redis

**Scenario**: 100 users checking URLs over 1 hour

```
User 1 → Analyze "phishing-site.com" → [3s] → Cache stored locally
User 2 → Analyze "phishing-site.com" → [3s] → Different server! 
         No cache hit → Full compute again ❌

Total API calls: ~100 (to VT, SB, FC)
Total latency: 300s+ of wasted compute time
```

### After Redis

```
User 1 → Analyze "phishing-site.com" → [3s] → Stored in Redis
User 2 → Analyze "phishing-site.com" → [<1ms] ← Instant hit! ✅

Repeat patterns...
User 99 → Analyze "phishing-site.com" → [<1ms] ← Cache!

Total API calls: ~5-10 (same URLs, cached)
Total latency: 3s + 99×(<1ms) = ~3.1s
Savings: 97% fewer API calls! 💰
```

---

## Integration Points

### 1. Environment Variables

```bash
# .env
REDIS_URL=redis://localhost:6379/0
CACHE_HOT_TTL=600          # 10 minutes
CACHE_WARM_TTL=2592000    # 30 days
```

### 2. Docker Compose

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes  # Persistence
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  backend:
    depends_on:
      redis:
        condition: service_healthy
    environment:
      - REDIS_URL=redis://redis:6379/0
```

### 3. Code Integration

**Current** (no Redis):
```python
result = url_cache.get(url)  # SQLite only
```

**With Redis**:
```python
cache_manager = CacheManager(
    redis_url=os.getenv("REDIS_URL"),
    db_path="url_cache.db"
)
result = cache_manager.get(url)  # Redis → SQLite → Compute
```

---

## Cost Analysis

### Infrastructure

| Component | Cost | Size | Notes |
|-----------|------|------|-------|
| Render Web Service | ~$7-15/mo | 1 GB | App logic |
| **Redis Cache** | ~$5-10/mo | 128 MB | Shared cache |
| SQLite DB | Free | ~100 MB | Persistent warm cache |

**Monthly Savings from fewer API calls**: $10-20/mo  
**Total added cost**: ~$5-10/mo  
**Net benefit**: $0-15/mo savings 💰

### API Quota Savings

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| VT calls/day | 500 | 50-100 | **80-90%** 🎯 |
| Cost/day | ~$0.05 | ~$0.01 | **80%** 💰 |
| Annual cost | ~$18/year | ~$4/year | **$14/year** |

---

## Implementation Timeline (Semana 2)

### Day 1-2: Implementation (2.5 hours)

1. **Create cache_manager.py** (30 min)
   - Redis connection logic
   - Fallback handling
   - Health checks

2. **Update phishing_service.py** (30 min)
   - Replace url_cache with cache_manager
   - Add error handling

3. **Docker Compose** (30 min)
   - Add Redis service
   - Configure persistence
   - Health checks

4. **Environment Config** (30 min)
   - .env example
   - Render environment variables
   - Graceful degradation

5. **Tests** (20 min)
   - Cache hit/miss scenarios
   - Redis connection failure
   - Performance benchmarks

### Day 3: Validation (1 hour)

1. Local testing with docker-compose
2. Performance benchmarks
3. Cache hit ratio measurement

---

## Monitoring

### Metrics to Track

```python
# In /metrics endpoint
cache_hit_ratio = Gauge(
    'cache_hit_ratio',
    'Hit ratio across all cache layers'
)

redis_latency = Histogram(
    'redis_latency_ms',
    'Redis response time'
)

cache_memory_usage = Gauge(
    'redis_memory_bytes',
    'Redis memory usage'
)
```

### Health Checks

```python
@app.get("/health")
def health():
    redis_ok = test_redis_connection()
    return {
        "status": "healthy",
        "cache_l0_redis": redis_ok,
        "cache_l1_sqlite": test_sqlite_connection(),
    }
```

---

## Why Redis (Not Memcached)?

| Feature | Redis | Memcached |
|---------|-------|-----------|
| **Persistence** | ✅ Yes (RDB/AOF) | ❌ No |
| **Data structures** | ✅ Rich (sets, lists, etc) | ❌ Strings only |
| **Replication** | ✅ Yes | ❌ No |
| **Pub/Sub** | ✅ Yes | ❌ No |
| **Atomic operations** | ✅ Yes | ❌ No |

**For us**: Persistence + simplicity = Redis ✅

---

## Fallback Strategy

If Redis becomes unavailable:

```python
def get_with_fallback(url):
    try:
        # Try Redis first
        if cache_manager.redis:
            return cache_manager.redis.get(url)
    except Exception as e:
        logger.warning(f"Redis error, falling back to SQLite: {e}")
    
    # Fallback to SQLite (always works)
    return cache_manager.sqlite.get(url)

# If both fail → run full analysis (expensive but works)
```

**User Impact**: None! Just slightly slower (still <100ms from SQLite)

---

## Summary

**Redis enables**:
1. ⚡ **Speed**: <1ms cache hits
2. 🔄 **Distribution**: Shared across instances
3. 🛡️ **Resilience**: Survives deploys
4. 💰 **Savings**: 80% fewer API calls
5. 📈 **Scale**: Ready for 10x growth

**Cost**: ~$5-10/month  
**Benefit**: $10-20/month in API savings + better UX  
**Risk**: Low (graceful fallback to SQLite)

---

**Status**: Ready to implement in Week 2 ✅

