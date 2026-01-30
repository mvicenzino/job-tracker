# Stride - Design & Architecture Document

## Overview

Stride is a full-stack job search management platform that helps users organize applications, track interviews, manage networking contacts, and research companies — all in one dashboard. It includes a web application, CLI tool, and Chrome extension for LinkedIn data capture.

**Live URL**: https://stride-jobs.vercel.app/
**Repository**: https://github.com/mvicenzino/job-tracker

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask 2.0+ (Python) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM | SQLAlchemy 2.0+ |
| Auth | Flask-Login, pbkdf2:sha256 hashing |
| Deployment | Vercel (serverless Python) |
| Frontend | Vanilla HTML5/CSS3/JS (no framework) |
| Font | Inter (Google Fonts) |
| Extension | Chrome Manifest V3 |
| Testing | pytest 7.0+, pytest-cov |
| PDF Parsing | PyPDF2 3.0+ |

### Python Dependencies

- sqlalchemy>=2.0.0
- flask>=2.0.0
- flask-login>=0.6.0
- psycopg2-binary>=2.9.0
- PyPDF2>=3.0.0
- pytest>=7.0.0, pytest-cov>=4.0.0

---

## Architecture

### Pattern: Layered Architecture with Repository + Service Patterns

```
Database (SQLite/PostgreSQL)
    ↕
src/database/connection.py     — SQLAlchemy engine & session management
    ↕
src/models/                    — ORM models (12 models, 11 tables)
    ↕
src/repositories/              — Data access layer (8 repositories)
    ↕
src/services/job_hunt.py       — Business logic orchestration
    ↕
src/web/routes/                — Flask blueprints (8 route modules)
    ↕
src/web/templates/             — Jinja2 HTML templates (24+ files)
src/web/static/                — CSS, JS, images
```

### Directory Structure

```
job-hunt-tracker/
├── api/
│   └── index.py                    # Vercel serverless entry point
├── chrome-extension/
│   ├── manifest.json               # Manifest V3 config
│   ├── content.js                  # LinkedIn page scraper
│   ├── popup.html                  # Extension popup UI
│   ├── popup.js                    # Extension logic & API calls
│   └── icons/                      # Extension icons (16, 48, 128px)
├── src/
│   ├── __init__.py
│   ├── cli.py                      # CLI interface (20+ commands)
│   ├── database/
│   │   └── connection.py           # SQLAlchemy setup
│   ├── models/
│   │   ├── __init__.py             # Base model + exports
│   │   ├── user.py                 # User model
│   │   ├── company.py              # Company model
│   │   ├── job.py                  # Job model
│   │   ├── application.py          # Application model + status enum
│   │   ├── contact.py              # Contact model + type enum
│   │   ├── event.py                # Event model + type enum
│   │   ├── note.py                 # Note model
│   │   └── tag.py                  # Tag + EntityTag models
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── user_repository.py
│   │   ├── company_repository.py
│   │   ├── job_repository.py
│   │   ├── application_repository.py
│   │   ├── contact_repository.py
│   │   ├── event_repository.py
│   │   ├── note_repository.py
│   │   └── tag_repository.py
│   ├── services/
│   │   └── job_hunt.py             # High-level business logic
│   └── web/
│       ├── app.py                  # Flask app factory
│       ├── helpers.py              # Shared route helpers
│       ├── routes/
│       │   ├── auth.py             # Login, register, logout
│       │   ├── public.py           # Landing, terms, privacy, demo
│       │   ├── dashboard.py        # Dashboard, pipeline views
│       │   ├── applications.py     # Application CRUD
│       │   ├── companies.py        # Company management
│       │   ├── jobs.py             # Job listings
│       │   ├── contacts.py         # Contact management
│       │   ├── schedule.py         # Events & calendar
│       │   ├── settings.py         # User settings, API keys, resume
│       │   └── api.py              # REST API for Chrome extension
│       ├── templates/
│       │   ├── base.html           # Base layout (nav, footer)
│       │   ├── landing.html        # Marketing landing page
│       │   ├── login.html          # Auth: login
│       │   ├── register.html       # Auth: register
│       │   ├── dashboard.html      # Main dashboard
│       │   ├── pipeline.html       # Kanban pipeline view
│       │   ├── companies.html      # Company list
│       │   ├── company_detail.html # Company detail
│       │   ├── jobs.html           # Job list
│       │   ├── job_detail.html     # Job detail
│       │   ├── contacts.html       # Contact list
│       │   ├── contact_detail.html # Contact detail
│       │   ├── schedule.html       # Calendar/schedule view
│       │   ├── settings.html       # User settings
│       │   ├── setup.html          # Chrome extension onboarding
│       │   ├── privacy.html        # Privacy policy
│       │   ├── terms.html          # Terms of service
│       │   └── components/         # Reusable form components
│       └── static/
│           ├── css/
│           │   ├── style.css       # Main app styles (3000+ lines)
│           │   └── landing.css     # Landing page styles (700+ lines)
│           ├── js/
│           │   └── main.js         # App JavaScript
│           └── img/
│               ├── favicon.svg
│               ├── stride-logo.svg
│               ├── stride-logo-transparent.svg
│               ├── stride-logo-newsletter.svg
│               ├── stride-logo-white-bg.svg
│               └── stride-icon-ios.svg
├── tests/
│   ├── test_models.py
│   ├── test_repositories.py
│   └── test_services.py
├── requirements.txt
├── vercel.json
├── run_web.py
├── migrate_db.py
└── update_user.py
```

---

## Data Model

### Entity Relationship Diagram

```
User (1) ──────┬──── (*) Company
               │         │
               │         ├──── (*) Job
               │         │       │
               │         │       └──── (*) Application
               │         │               │
               │         └──── (*) Contact ──── (*) Event
               │                                    │
               └──── (*) Note ◄─────────────────────┘
                     (*) Tag ◄── EntityTag (polymorphic)
```

### Models

**User**
| Field | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| email | String(120) | Unique |
| password_hash | String(256) | pbkdf2:sha256 |
| api_key | String(64) | For Chrome extension auth |
| is_active | Boolean | Default true |
| resume_text | Text | Parsed resume content |
| resume_filename | String(255) | Uploaded filename |
| created_at | DateTime | Auto-set |
| updated_at | DateTime | Auto-updated |

**Company**
| Field | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| user_id | Integer | FK → users |
| name | String(200) | Required |
| website | String(500) | |
| industry | String(100) | |
| size | String(50) | |
| location | String(200) | |
| description | Text | |
| culture_notes | Text | |
| glassdoor_rating | Float | |
| linkedin_url | String(500) | |

**Job**
| Field | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| user_id | Integer | FK → users |
| company_id | Integer | FK → companies |
| title | String(200) | Required |
| description | Text | |
| requirements | Text | |
| salary_min / salary_max | Integer | |
| salary_currency | String(3) | Default "USD" |
| location | String(200) | |
| remote_type | String(20) | remote, hybrid, onsite |
| job_url | String(500) | |
| source | String(50) | LinkedIn, Indeed, referral, etc. |
| is_active | Boolean | |
| is_flagged | Boolean | |

**Application**
| Field | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| user_id | Integer | FK → users |
| job_id | Integer | FK → jobs |
| status | Enum | 12 statuses (see below) |
| date_applied | Date | |
| date_response | Date | |
| date_closed | Date | |
| resume_version | String(100) | |
| cover_letter | Text | |
| referral_contact_id | Integer | FK → contacts |
| offered_salary / bonus / equity | Various | |
| rejection_reason | Text | |
| lessons_learned | Text | |
| excitement_level | Integer | 1-5 scale |

**Application Status Enum (12 stages):**
```
interested → preparing → applied → screening → interviewing →
final_round → offer → negotiating → accepted
                                  ↘ rejected
                                  ↘ withdrawn
                                  ↘ ghosted
```

**Contact**
| Field | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| user_id | Integer | FK → users |
| company_id | Integer | FK → companies |
| name | String(200) | Required |
| email | String(120) | |
| phone | String(20) | |
| linkedin_url | String(500) | |
| title | String(200) | |
| contact_type | Enum | 10 types |
| how_we_met | Text | |
| relationship_strength | Integer | 1-5 |
| last_contact_date | Date | |
| next_followup_date | Date | |
| notes | Text | |

**Contact Types:** recruiter, hiring_manager, employee, mentor, referral, alumni, friend, former_colleague, headhunter, other

**Event**
| Field | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| user_id | Integer | FK → users |
| application_id | Integer | FK → applications |
| contact_id | Integer | FK → contacts |
| title | String(200) | Required |
| event_type | Enum | 16 types |
| description | Text | |
| start_time / end_time | DateTime | |
| is_all_day | Boolean | |
| location | String(200) | |
| meeting_link | String(500) | |
| prep_notes | Text | |
| questions_to_ask | Text | |
| completed | Boolean | |
| outcome_notes | Text | |
| went_well | Boolean | |
| reminder_minutes | Integer | |

**Event Types (16):** phone_screen, video_interview, onsite_interview, technical_interview, behavioral_interview, panel_interview, coffee_chat, networking_event, career_fair, follow_up, offer_call, negotiation_call, application_deadline, task_deadline, reminder, other

**Note**
| Field | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| company_id / job_id / application_id / contact_id / event_id | Integer | Polymorphic FKs |
| title | String(200) | |
| content | Text | |
| note_type | String(50) | |

**Tag / EntityTag**
- Tag: id, name (unique), color, description
- EntityTag: id, tag_id, entity_type, entity_id (polymorphic many-to-many)

---

## Authentication & Security

### Auth Flow
1. **Register**: Email + password (8+ char) → hash → auto-login
2. **Login**: Email + password → verify hash → session cookie (30-day)
3. **Session**: Flask-Login with persistent cookies
4. **API Auth**: X-API-Key header (secrets.token_hex(32))

### Security Measures
- Password hashing: pbkdf2:sha256
- Session cookies: SECURE, HTTPONLY, SAMESITE=Lax (production)
- HTTPS-only cookies in production
- User-scoped queries (all data filtered by user_id)
- CORS headers for Chrome extension API
- Login-required decorators on all protected routes

---

## API Endpoints

| Method | Endpoint | Purpose | Auth |
|--------|----------|---------|------|
| PATCH | /api/applications/{id}/status | Update app status | Session/API key |
| PATCH | /api/applications/{id} | Update application | Session/API key |
| PATCH | /api/jobs/{id} | Update job | Session/API key |
| PATCH | /api/companies/{id} | Update company | Session/API key |
| POST | /api/contacts | Create/update contact | API key |
| POST | /api/companies | Create/update company | API key |
| POST | /api/jobs | Create job | API key |
| OPTIONS | /api/* | CORS preflight | None |

---

## Chrome Extension

### "Stride - LinkedIn Import"

**Purpose**: One-click data capture from LinkedIn into the Stride app.

**Page Detection**:
- `/in/` → LinkedIn Profile → Contact form
- `/company/` → Company Page → Company form
- `/jobs/view/` → Job Listing → Job form

**Data Extraction** (content.js):
- Multi-layered selector strategy for resilience against LinkedIn DOM changes
- Falls back through multiple CSS selectors for each field
- Uses dt/dd structured data extraction for company "About" sections
- Regex-based extraction for employee count ranges

**Popup UI** (popup.html/popup.js):
- Dynamic form display based on detected page type
- Server URL + API key configuration
- Connection status indicator
- Auto-populated fields from page scraping
- Submit to Stride API with error handling

**Manifest V3 Config**:
- Permissions: activeTab, storage
- Host permissions: linkedin.com, stride-jobs.vercel.app
- Icons: 16x16, 48x48, 128x128 PNG

---

## Frontend Design System

### Brand Identity

**Name**: Stride
**Tagline**: "Stride into your next role"
**Logo**: Double-chevron icon (forward motion) + wordmark

**Logo Assets**:
| File | Use Case |
|------|----------|
| stride-logo-transparent.svg | App navbar/footer (combined icon + wordmark) |
| stride-logo-newsletter.svg | Marketing/newsletter (indigo pill background) |
| stride-logo-white-bg.svg | Dark backgrounds (white card) |
| stride-icon-ios.svg | App icon (1024x1024) |
| favicon.svg | Browser tab icon |
| stride-logo.svg | Icon-only mark (currentColor) |

### Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| --color-primary | #6366f1 | Indigo — buttons, links, brand |
| --color-primary-hover | #4f46e5 | Darker indigo — hover states |
| --color-primary-light | #e0e7ff | Light indigo — backgrounds |
| --color-accent | #8b5cf6 | Violet — gradients, highlights |
| --color-success | #10b981 | Green — accepted, positive |
| --color-warning | #f59e0b | Amber — attention, pending |
| --color-danger | #ef4444 | Red — rejected, errors |
| --color-info | #06b6d4 | Cyan — informational |

**Gradient**: `linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #06b6d4 100%)`

### Typography

- **Font**: Inter (Google Fonts)
- **Fallback**: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif
- **Letter spacing**: -0.01em
- **Line height**: 1.6
- **Font smoothing**: antialiased

### Spacing Scale

| Token | Value |
|-------|-------|
| --space-1 | 0.25rem (4px) |
| --space-2 | 0.5rem (8px) |
| --space-3 | 0.75rem (12px) |
| --space-4 | 1rem (16px) |
| --space-5 | 1.25rem (20px) |
| --space-6 | 1.5rem (24px) |
| --space-8 | 2rem (32px) |
| --space-10 | 2.5rem (40px) |
| --space-12 | 3rem (48px) |

### Border Radius

| Token | Value |
|-------|-------|
| --radius-sm | 6px |
| --radius-md | 8px |
| --radius-lg | 12px |
| --radius-xl | 16px |
| --radius-2xl | 20px |
| --radius-full | 9999px |

### Shadows

- xs, sm, md, lg, xl — progressive depth system
- Refined, soft shadows for modern aesthetic

### UI Components
- Card-based layouts
- Status badges with color coding
- Form inputs with focus rings
- Buttons (primary, ghost, demo, danger)
- Navigation with hamburger mobile menu
- Footer with link groups
- Stats tiles (clickable)
- Pipeline Kanban columns
- Calendar event cards

---

## Features Catalog

### Dashboard
- Application statistics by status (tile cards)
- Today's events + upcoming 7-day preview
- Contacts needing follow-up
- Stale applications (14+ days awaiting response)
- Quick-action links

### Pipeline
- Kanban-style board with 12 status columns
- Drag-and-drop status updates
- Application cards with company, title, date

### Applications
- Quick apply (company + title shortcut)
- Full application form (excitement level, resume version, cover letter)
- Status progression tracking with dates
- Referral contact linking
- Offer details (salary, bonus, equity)
- Rejection tracking with lessons learned
- Notes per application

### Companies
- Company profiles (industry, size, location, website)
- Culture notes and Glassdoor ratings
- LinkedIn URL linking
- Search by name

### Jobs
- Job listings with salary ranges
- Remote type classification
- Source tracking
- Flag/save jobs
- Search and filter

### Contacts
- Contact profiles with types (recruiter, hiring manager, etc.)
- Relationship strength (1-5)
- Follow-up scheduling
- Interaction logging
- CSV export
- Search and filter

### Schedule
- Calendar view (7, 14, 30 day windows)
- 16 event types with color coding
- Interview scheduling with auto-status update
- Prep notes and questions to ask
- Meeting links
- Completion tracking with outcomes

### Settings
- API key generation (Chrome extension)
- Resume upload (PDF) or paste
- Account management

### Demo Mode
- Pre-populated sample data (8 companies, 8 jobs, 5 contacts, 10 events)
- Demo badge in navbar
- No account required to explore

### Landing Page
- Hero: "Your Job Search, Finally Organized"
- Subtitle: "Take it in Stride"
- 6 feature highlights (Pipeline, Scheduler, Contacts, Research, Dashboard, Reminders)
- 3-step "How It Works"
- CTAs: Start Tracking Free, Try Demo
- Footer with product links, legal pages

---

## Deployment

### Vercel Configuration (vercel.json)
```json
{
  "version": 2,
  "builds": [
    { "src": "api/index.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/static/(.*)", "dest": "/api/index.py" },
    { "src": "/(.*)", "dest": "/api/index.py" }
  ]
}
```

### Entry Point (api/index.py)
- Imports Flask app from `src.web.app`
- Runs database migrations on startup
- Exports `app` for Vercel's Python runtime

### Environment Variables (Production)
- `DATABASE_URL` — PostgreSQL connection string
- `SECRET_KEY` — Flask session secret
- `FLASK_ENV` — production

### Local Development
```bash
pip install -r requirements.txt
python run_web.py
# App runs on http://localhost:5001
```

---

## Testing

### Framework: pytest

**Test Files:**
- `tests/test_models.py` — Model creation, relationships, validation
- `tests/test_repositories.py` — Repository CRUD operations
- `tests/test_services.py` — Service business logic

**Approach:**
- Temporary SQLite databases for test isolation
- Fixtures: db session, test user
- Tests for model relationships, status workflows, data integrity

```bash
pytest tests/ -v
pytest tests/ --cov=src
```

---

## CLI Interface

**Command**: `jobhunt [command] [args]`

| Command | Alias | Description |
|---------|-------|-------------|
| dashboard | d | Overview with stats |
| apply | a | Quick apply (company, title, url, source) |
| status | s | Update application status |
| pipeline | p | View by status |
| companies | — | List/search companies |
| add-company | — | Create company |
| jobs | — | List/search jobs |
| add-job | — | Create job |
| contacts | c | List/search contacts |
| add-contact | — | Create contact |
| log-contact | — | Log interaction |
| schedule | — | View calendar |
| add-event | — | Schedule event |
| interview | i | Schedule interview |
| complete | — | Mark event done |
| notes | — | Search notes |
| note | — | Add note |

---

## Statistics

| Metric | Count |
|--------|-------|
| Source files | ~40 |
| Lines of code | ~6,000+ |
| Database tables | 11 |
| Data models | 12 |
| Repositories | 8 |
| Route blueprints | 8 |
| Flask routes | 40+ |
| API endpoints | 7 |
| CLI commands | 20+ |
| Event types | 16 |
| Application statuses | 12 |
| Contact types | 10 |
| HTML templates | 24+ |
| CSS variables | 100+ |
| Logo assets | 6 |
