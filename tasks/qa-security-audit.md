# Stride QA Security Audit — Tracking

**Audit Date:** 2026-02-22
**Total Issues Found:** 23
**Fixed:** 15 across 2 passes

### Pass 1 — Critical + High (items 1-9)
- **Commit:** `a6c248f`
- **Files:** `auth.py`, `app.py`, `api.py`, `settings.py`, `public.py`, `requirements.txt`, 27 templates
- **Scope:** Open redirect, CSRF, CORS wildcard, secret key enforcement, error sanitization, health endpoint leak, pro upgrade disabled

### Pass 2 — Medium + Low cleanup (items 10-13, 15, 21)
- **Date:** 2026-02-22
- **Files:** `api.py`, `user.py`, `public.py`, `feedback.py`, `auth.py`
- **Scope:** Mass assignment protection, demo pro bypass, cron auth hardening, feedback privacy, email validation, duplicate route removal
- **Tests:** 79 passed, 1 pre-existing failure (unrelated dashboard query)

---

## CRITICAL — Fixed

### 1. Open Redirect on Login `next` Parameter
- **File:** `src/web/routes/auth.py`
- **Fix:** Validate `next` param rejects absolute URLs (scheme/netloc check). Falls back to dashboard.
- **Status:** DONE
- **Verify:** `GET /login?next=https://evil.com` -> login -> should redirect to `/dashboard`, NOT evil.com

### 2. `/admin-login` Route — Public Backdoor
- **File:** `src/web/routes/auth.py`
- **Status:** ALREADY ABSENT — route did not exist in current codebase
- **Verify:** `GET /admin-login` returns 404

### 3. Free Pro Upgrade Endpoint (No Payment)
- **File:** `src/web/routes/settings.py`
- **Fix:** Route returns `501 Not Implemented` instead of granting Pro.
- **Status:** DONE
- **Verify:** `POST /settings/upgrade` returns 501 JSON

---

## HIGH — Fixed

### 4. No CSRF Protection on Any Form
- **Files:** `src/web/app.py`, `requirements.txt`, 27 template files
- **Fix:** Added `flask-wtf`, initialized `CSRFProtect(app)`, added `csrf_token()` hidden input to all POST forms. API blueprint exempted (uses API key auth, not cookies).
- **Status:** DONE
- **Verify:** Submit any form without token -> 400 CSRF error. Normal form submission works.

### 5. `/api/health` Leaks Database Schema
- **File:** `src/web/routes/api.py`
- **Fix:** Removed `inspect()` column introspection. Now only runs `SELECT 1` connectivity check.
- **Status:** DONE
- **Verify:** `GET /api/health` returns `{"status":"ok","checks":{"database":"connected"}}` — no column names.

### 6. Hardcoded Default `SECRET_KEY`
- **File:** `src/web/app.py`
- **Fix:** `RuntimeError` raised on startup if `VERCEL` env var is set and `SECRET_KEY` is the default dev value.
- **Status:** DONE
- **Verify:** Local dev still works (no VERCEL env). Production deploy without SECRET_KEY fails to start.

### 7. CORS `Access-Control-Allow-Origin: *` on Mutation Endpoints
- **File:** `src/web/routes/api.py`
- **Fix:** Dynamic origin checking via `_get_cors_origin()`. Allows: `APP_URL` env var, `chrome-extension://` origins, `localhost`/`127.0.0.1` dev servers. All other origins rejected.
- **Status:** DONE
- **Verify:** API response from browser on different domain has no `Access-Control-Allow-Origin` header. Chrome extension and same-origin requests work normally.
- **Note:** Set `APP_URL` env var on Vercel (e.g., `https://stride-jobs.vercel.app`) for production CORS.

### 8. Raw Exception Messages Returned to Client
- **File:** `src/web/routes/api.py`, `src/web/routes/settings.py`
- **Fix:** All `str(e)` replaced with generic `"Internal server error"`. Real exceptions logged via `app.logger.exception()`.
- **Status:** DONE
- **Verify:** Trigger a 500 error -> response says "Internal server error", not a Python traceback.

### 9. Full Traceback Rendered in Demo Error
- **File:** `src/web/routes/public.py`
- **Fix:** Replaced `traceback.format_exc()` HTML with `flash('Demo setup failed...', 'error')` + redirect to landing.
- **Status:** DONE
- **Verify:** If demo seed fails, user sees flash message on landing page, not raw traceback.

---

## MEDIUM — Fixed

### 10. Mass Assignment on API Update Endpoints
- **File:** `src/web/routes/api.py`
- **Fix:** Added `ALLOWED_APPLICATION_FIELDS`, `ALLOWED_JOB_FIELDS`, `ALLOWED_COMPANY_FIELDS` whitelists. All 3 PATCH handlers filter incoming data against whitelists before passing to `update()`. Blocks `user_id`, `id`, `subscription_tier`, `company_id`, `created_at`, etc.
- **Status:** DONE

### 11. Demo Email Grants Free Pro Access
- **Files:** `src/models/user.py`, `src/web/routes/public.py`
- **Fix:** Removed email check from `is_pro` property — now purely checks `subscription_tier == 'pro'`. Demo seed explicitly sets `subscription_tier = 'pro'` on create and on every visit.
- **Status:** DONE

### 12. Cron Endpoints Unprotected When `CRON_SECRET` Not Set
- **File:** `src/web/routes/api.py`
- **Fix:** Both cron endpoints now return 401 if `CRON_SECRET` not set and `VERCEL` env var is present (production). Local dev still works without secret.
- **Status:** DONE

### 13. `/feedback/list` Shows All Users' Feedback
- **File:** `src/web/routes/feedback.py`
- **Fix:** Added `Feedback.user_id == current_user.id` filter to query.
- **Status:** DONE

### 14. No Rate Limiting on Login or API
- **Issue:** No `Flask-Limiter`. Brute-force and API abuse unrestricted.
- **Fix needed:** Add `flask-limiter` with sensible defaults.
- **Status:** NOT FIXED (requires new dependency)

### 15. No Email Validation on Registration
- **File:** `src/web/routes/auth.py`
- **Fix:** Added `EMAIL_RE` regex pattern. Register route validates email format before DB lookup. No new dependencies.
- **Status:** DONE

---

## LOW — Not Fixed (Backlog)

### 16. Avatar Upload Validates Extension Only, Not MIME Type
### 17. ICS Meeting Links Not Validated
### 18. No 404/500 Custom Error Pages
### 19. No Password Reset Flow
### 20. No Account Deletion / GDPR Data Export
### 21. Duplicate Route Definitions in `api.py`
- **Fix:** Removed older `api_get_contact` (shadowed by `api_get_contact_detail`) and older `api_contacts_search` (shadowed by `api_search_contacts`). Kept newer versions using shared helpers.
- **Status:** DONE
### 22. Google Sheets Export Is a Stub
### 23. Dependencies: No Upper Bounds, pytest in Prod Requirements

---

## Deployments

| Site | URL | Status |
|------|-----|--------|
| stride-jobs (primary) | https://stride-jobs.vercel.app | Live — Pass 1 + Pass 2 deployed 2026-02-22 |
| stride-feature-branch | https://stride-feature-branch.vercel.app | Live — auto-deployed from same push |

Both verified: `/demo` returns 302 → `/dashboard`, demo data renders (Stripe, Notion, Figma, Anthropic).

---

## Post-Deploy Checklist

- [x] Test demo flow: `GET /demo` and `GET /demo?refresh=1` — both 302 → dashboard
- [ ] Set `APP_URL` env var on Vercel (e.g., `https://stride-jobs.vercel.app`)
- [ ] Verify `SECRET_KEY` is set in Vercel env vars (app won't start without it)
- [ ] Set `CRON_SECRET` env var on Vercel (medium priority — item 12)
- [ ] Test login with `?next=https://evil.com` redirects to dashboard
- [ ] Verify `/api/health` returns no column names
- [ ] Verify `POST /settings/upgrade` returns 501
- [ ] Test Chrome extension still works with tightened CORS
- [ ] Full page walkthrough: landing -> login -> dashboard -> applications -> pipeline
