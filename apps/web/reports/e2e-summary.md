# E2E Test Summary Report

**Date:** 2026-02-22
**Project:** iconsai-scraping (apps/web)
**Status:** ⚠️ PARTIAL PASS

## Environment
```
Node: v22.12.0
NPM: 10.9.0
Playwright: 1.58.2
Base URL: http://localhost:3000
```

## Test Results

| Status | Count |
|--------|-------|
| Passed | 7 |
| Failed | 3 |
| Total | 10 |

## Passed Tests
1. ✅ smoke - home page loads without errors
2. ✅ login page - form visible and interactive
3. ✅ navigation - header elements are interactive
4. ✅ crawl all discoverable pages
5. ✅ forms - inputs accept text
6. ✅ buttons - all visible buttons are enabled
7. ✅ responsive - page renders on mobile viewport

## Failed Tests

### 1. dashboard - loads when authenticated
- **Category:** `AUTH_FLOW_BROKEN`
- **Error:** Timeout waiting for networkidle on /dashboard
- **Root Cause:** Dashboard requires real JWT authentication. Fake token in localStorage is validated by TanStack Query which makes API calls that fail with 401.
- **Severity:** Medium
- **Evidence:** `test-results/critical-Critical-Tests-dashboard---loads-when-authenticated-chromium/trace.zip`

### 2. modals - module cards are clickable
- **Category:** `AUTH_FLOW_BROKEN`
- **Error:** Same as above - cannot reach dashboard
- **Severity:** Medium
- **Evidence:** `test-results/critical-Critical-Tests-modals---module-cards-are-clickable-chromium/trace.zip`

### 3. modal interactions (crawler)
- **Category:** `AUTH_FLOW_BROKEN`
- **Error:** Same as above - cannot reach dashboard
- **Severity:** Medium
- **Evidence:** `test-results/crawl-Crawler---Massive-UI-Testing-modal-interactions-chromium/trace.zip`

## Coverage

| Metric | Value |
|--------|-------|
| Pages Visited | 3 |
| Actions Executed | 7 |
| Elements Interacted | 7 |
| Routes Discovered | `/`, `/docs`, `/redoc`, `/dashboard` |

## Recommendations

1. **Provide E2E Test Credentials:** Set `E2E_TEST_USER_EMAIL` and `E2E_TEST_USER_PASSWORD` environment variables
2. **Mock API Responses:** Use Playwright's route interception to mock `/auth/me` endpoint
3. **Add Setup Project:** Create auth setup that logs in and saves `storageState.json`

## Commands
```bash
# Run all tests
E2E_BASE_URL=http://localhost:3000 npm run test:e2e

# View report
npm run test:e2e:report

# Debug with UI
npm run test:e2e:ui
```

## Artifacts
- `playwright-report/` - HTML report
- `test-results/` - Traces, screenshots, videos
