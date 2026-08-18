# 🚀 Two-Week Complete Roadmap

**Dates**: 2026-08-18 to 2026-08-31  
**Goal**: Production-ready API + Extension  
**Status**: Ready to execute

---

## Week 1: Backend Stabilization + Extension Critical Fixes

### Backend (Completed ✅)
- [x] Fix deprecation warnings (datetime.utcnow)
- [x] Clean up all linting (0 errors)
- [x] Stress testing suite (8 tests, 324 total)
- [x] Performance baselines + SLA targets
- [x] OpenTelemetry infrastructure

### Extension (This week - 4 hours)

#### Day 1-2: Critical Fixes (P0-P1)

**Task 1: Fix Hardcoded Backend URL (30 min)**
- File: `extension/services/api_client.js`
- Change: Remove hardcoded Render URL
- Add: Dynamic config from chrome.storage.local
- Default: `http://localhost:8000`

**Task 2: Implement extractFromActivePage() (45 min)**
- File: `extension/sidebar/sidebar.js`
- Add: Missing function to extract page text
- Update: manifest.json permissions (add scripting)
- Update: chrome.scripting.executeScript call

**Task 3: Better Error Messages (30 min)**
- Files: `popup.js`, `sidebar.js`
- Add: ERROR_MESSAGES mapping (429, 404, 500, timeout)
- Update: All error handlers to use friendly messages
- Test: Different error scenarios

**Task 4: Connection Health Check (45 min)**
- New: `extension/background/health_check.js`
- Add: onInstalled listener
- Add: Periodic alarms (every 5 min)
- Update: manifest.json permissions (alarms)
- Display: Badge/indicator when offline

#### Day 3: Testing + Polish (2 hours)
- Manual testing: All features working
- Test extraction: Extract page button working
- Test connection: Health check displays status
- Test errors: User-friendly error messages
- Fix: Any UX issues

**Week 1 Extension Total**: ~4 hours

---

## Week 2: Backend Integration + Deployment

### Day 1-2: Redis Caching (3 hours)

**Task 5: Implement Redis Layer (2.5 hours)**
- File: `backend/app/utils/cache_manager.py` (NEW)
- Architecture:
  - L0: Redis (sub-millisecond, 10 min TTL)
  - L1: SQLite (warm, 30-day TTL)
  - L2: Compute (on-demand)
- Graceful degradation if Redis unavailable
- Config: `REDIS_URL` env var

**Task 6: Add Redis to Docker Compose (30 min)**
- Add Jaeger service (already done)
- Add Redis service
- Update backend depends_on

**Task 7: Redis Tests (30 min)**
- Test hit ratio improvement
- Test fallback to SQLite
- Test performance: <1ms cache hits

### Day 3-4: Deployment Validation (3 hours)

**Task 8: Render Deployment (2 hours)**
- Setup Web Service on Render
- Configure env vars:
  - VIRUSTOTAL_API_KEY
  - SAFE_BROWSING_API_KEY
  - FACT_CHECK_API_KEY
  - API_KEY (optional)
  - ENVIRONMENT=production
- Set Dockerfile path: `backend/Dockerfile`
- Monitor cold start time (target: <90s)
- Test endpoints:
  - GET /health → 200
  - POST /predict → 200
  - GET /metadata → includes model info

**Task 9: Extension Production Config (30 min)**
- Update default backend URL for production
- Add Render URL to manifest
- Test against production backend
- Update options page backend URL input

**Task 10: OpenTelemetry Integration (30 min)**
- Integrate init_tracing() in main.py
- Fix test isolation issue
- Ensure 324 tests pass
- Document tracing in docker-compose

### Day 5: Final QA + Documentation (2 hours)

**Task 11: Full Integration Testing (1 hour)**
- Test full pipeline: Extension → API → ML
- Verify cache layers working
- Check performance: P95 <5s
- Validate error handling

**Task 12: Documentation + Release Notes (1 hour)**
- Update README with new features
- Document Redis setup
- Create RELEASE_NOTES.md
- Update API_OPTIMIZATION.md with results

**Week 2 Backend Total**: ~6 hours

---

## Implementation Schedule

```
WEEK 1 (2026-08-18 to 2026-08-24)
├─ Day 1-2 (Mon-Tue): Extension Critical Fixes (4h)
│  ├─ Hardcoded URL
│  ├─ extractFromActivePage()
│  ├─ Error messages
│  └─ Health checks
├─ Day 3 (Wed): Extension Testing (1h)
├─ Day 4-5 (Thu-Fri): BUFFER / Backend Polish (2h)
└─ Total: ~7 hours (DONE: Deprecation + Linting + Tests)

WEEK 2 (2026-08-25 to 2026-08-31)
├─ Day 1-2 (Mon-Tue): Redis Caching (3h)
│  ├─ cache_manager.py
│  ├─ Docker compose
│  └─ Tests
├─ Day 3-4 (Wed-Thu): Render Deployment (3h)
│  ├─ Web Service setup
│  ├─ Env vars
│  ├─ Cold start validation
│  └─ Extension production config
├─ Day 5 (Fri): QA + Docs (2h)
│  ├─ Integration testing
│  └─ Release notes
└─ Total: ~8 hours
```

---

## Priority Matrix (by Week)

### Week 1 (Extension Critical - BLOCKING)

| Task | Effort | Impact | Status |
|------|--------|--------|--------|
| Hardcoded URL | 30m | P0 | Ready |
| extractFromActivePage() | 45m | P0 | Ready |
| Error messages | 30m | P1 | Ready |
| Health checks | 45m | P1 | Ready |

### Week 2 (Backend + Deployment)

| Task | Effort | Impact | Status |
|------|--------|--------|--------|
| Redis L0 cache | 2.5h | P1 | Ready |
| Render deployment | 2h | P0 | Ready |
| Extension prod config | 30m | P0 | Ready |
| OT integration | 30m | P2 | Ready |
| QA + Docs | 2h | P2 | Ready |

---

## Success Criteria

### Week 1
- [ ] Extension hardcoded URL removed
- [ ] Extract page button works
- [ ] User-friendly error messages
- [ ] Health check monitoring
- [ ] 324 tests still passing
- [ ] 0 linting errors

### Week 2
- [ ] Redis L0 cache working
- [ ] Deployment on Render successful
- [ ] Cold start < 90 seconds
- [ ] Extension configured for production
- [ ] Performance: P95 latency < 5s
- [ ] OpenTelemetry tracing integrated
- [ ] Full integration tests passing

---

## Risk Management

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Extension breaks on prod | Low | High | Test against Render URL |
| Redis connection fails | Low | Low | Graceful fallback to SQLite |
| Cold start too long | Low | Medium | Monitor, optimize models if needed |
| OT breaks tests | Medium | Medium | Investigate test isolation before integrating |
| Render deploy fails | Low | High | Test locally first, use staging |

---

## Rollback Plan

**Week 1 (Extension)**
- Revert commits if critical issues found
- Keep old backend URL in branch

**Week 2 (Backend)**
- If Redis breaks: Disable in code, fallback to SQLite
- If Render fails: Keep backend on localhost
- If OT fails: Deploy without tracing

---

## Deliverables

### End of Week 1
- ✅ Extension v1.0.2 (critical fixes)
- ✅ Performance baselines established
- ✅ Tracing infrastructure in place

### End of Week 2
- ✅ Extension v1.0.2 deployed to Chrome Store
- ✅ API v1.0 running on Render
- ✅ Redis caching active
- ✅ OpenTelemetry tracing live
- ✅ Full documentation + release notes
- ✅ 324 tests passing, 100% critical tests

---

## Metrics to Track

### Performance
- [ ] Cache hit ratio: target >50%
- [ ] P95 latency: target <5s
- [ ] Cold start: target <90s

### Reliability
- [ ] Error rate: target <1%
- [ ] Availability: target 99%
- [ ] Extension crashes: 0

### Code Quality
- [ ] Test coverage: 100% critical
- [ ] Linting errors: 0
- [ ] Security issues: 0

---

## Post-Deployment (Week 3+)

After Week 2 completion:
1. Monitor production metrics for 1 week
2. Gather user feedback
3. Plan Q4 features:
   - Batch URL analysis
   - Dark mode
   - Offline support with full cache
   - Advanced analytics dashboard

---

**Status**: Ready to execute ✅  
**Estimated Effort**: ~15 hours over 2 weeks  
**Complexity**: Medium (Extension + Redis + Deployment)  
**Risk Level**: Low (all changes tested, reversible)

