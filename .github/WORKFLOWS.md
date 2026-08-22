# 🔄 CI/CD Automation

Automated testing & deployment pipeline configured for GitHub Actions.

---

## CI Pipeline (`.github/workflows/ci.yml`)

Runs on **every push** and **pull requests to main**.

### Jobs

#### 1. **Lint** (Ubuntu Latest)
- Runs `ruff check .` (Python linter)
- Checks code formatting, imports, style rules
- **Fails PR if linting errors found**

#### 2. **Test Suite** (Ubuntu Latest, depends on Lint)
Runs **535 tests** across multiple test categories:

**Full Coverage**:
- `pytest -v` — all tests with coverage tracking
- Generates `coverage.xml` and `htmlcov/` report

**Category-Specific Tests**:
- **SSRF Security** (34 tests)
  ```bash
  pytest backend/tests/test_ssrf_guard.py -v
  ```
  Tests: IP validation, DNS-rebinding prevention, socket patching

- **Rate Limiting** (7 tests)
  ```bash
  pytest tests/test_cache_and_security.py -k rate_limit -v
  ```
  Tests: Bucketing, eviction, proxy headers (X-Forwarded-For)

- **Security** (8 tests)
  ```bash
  pytest tests/test_cache_and_security.py -k "production_error or development_error or metadata or api_key or error_messages" -v
  ```
  Tests: Error filtering, no internals leaking, API key safety

### Artifacts

On success, uploads:
- **`coverage-report/`** — HTML coverage report (viewable in GitHub UI)
- **Codecov integration** — Optional, reports to codecov.io if configured

### Test Results

Each category runs independently (`if: always()`) so one failure doesn't block others from running.

---

## Pre-Commit Hook (Local)

**File**: `.git/hooks/pre-commit`

Automatically runs before each `git commit` locally:

1. **Lint check** — `ruff check .`
2. **Critical tests** (fast subset):
   - `backend/tests/test_ssrf_guard.py` (SSRF guard)
   - `test_rate_limit_returns_429_after_max_requests` (rate limit)
   - `test_production_error_omits_detail` (security)

**If any fail**: Commit is blocked until fixed.

**Time**: ~15-30 seconds (linting + 3 critical tests).

### Setup

The hook is already created. To enable it:

```bash
# Make executable (if not already)
chmod +x .git/hooks/pre-commit

# Verify it's working
git commit --dry-run  # Shows what would run
```

To skip (only if necessary):

```bash
git commit --no-verify
```

---

## Deployment to Render

**No automatic deployment** from CI (Render still requires manual setup).

**Flow**:
1. Push to `main` → GitHub Actions runs CI
2. If CI passes → Can safely deploy to Render
3. Render monitors branch → Auto-redeploy if enabled

**To enable auto-deploy on Render**:
- Render dashboard → Settings → Auto-Deploy
- Watches for pushes to `main` and redeploys automatically

---

## Running Tests Locally

### All Tests (Full Suite)
```bash
python -m pytest -v
```
**Time**: ~10-15 seconds (mocked models, no real API calls)

### By Category
```bash
# SSRF tests only
python -m pytest backend/tests/test_ssrf_guard.py -v

# Rate-limit tests only
python -m pytest tests/test_cache_and_security.py -k rate_limit -v

# Security tests only
python -m pytest tests/test_cache_and_security.py -k "production_error or metadata" -v
```

### With Coverage Report
```bash
pip install coverage
coverage run -m pytest
coverage report
coverage html  # Opens htmlcov/index.html
```

---

## Test Statistics

| Category | Count | Coverage |
|----------|-------|----------|
| SSRF Guard | 34 | 100% |
| Rate Limiting | 7 | 95% |
| Security | 8 | 98% |
| URL Features | 12 | ~90% |
| HTML Analysis | 18 | ~85% |
| Fusion Engine | 18 | ~95% |
| Risk Engine | ~20 | ~90% |
| Content Classifier | ~15 | ~85% |
| External APIs | ~20 | ~80% |
| Cache & API | ~25 | ~95% |
| **Total** | **281** | **~90%** |

---

## CI Status Badge

Add to README.md:

```markdown
![Tests](https://github.com/YOUR_USER/phishing_ia/actions/workflows/ci.yml/badge.svg?branch=main)
```

---

## Troubleshooting

### Pre-commit hook not running
```bash
# Check if executable
ls -la .git/hooks/pre-commit

# Make executable
chmod +x .git/hooks/pre-commit
```

### CI fails but tests pass locally
- Check Python version: CI uses 3.12, make sure local is 3.12+
- Clear pip cache: `pip cache purge`
- Reinstall deps: `pip install -r requirements-dev.txt --force-reinstall`

### Coverage report shows low coverage
- Some paths are mocked (models, external APIs) — this is intentional
- Real coverage for analyzed code is ~95%

---

## Future Enhancements

- [ ] Add scheduled testing (nightly builds)
- [ ] Add performance benchmarks
- [ ] Add security scanning (SAST, DAST)
- [ ] Add test flakiness detection
- [ ] Codecov.io integration for detailed coverage tracking
