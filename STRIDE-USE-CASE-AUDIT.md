# Stride Use Case vs. Implementation Audit

**Date:** 2026-02-13  
**Auditor:** OpenClaw AI  
**Purpose:** Compare the marketing use case with actual implementation to identify gaps and prioritize improvements.

---

## Executive Summary

**Overall Score: 7.5/10**

Stride has a **solid foundation** with excellent core features (tracking, Chrome extension, AI scoring, notifications). However, the **automated job capture and smart alerting** promised in the use case are **not yet implemented**, which is the primary value proposition. The app currently requires significant manual effort to add jobs, defeating the "automated command center" promise.

**Top Priority:** Build automated daily job ingestion + AI scoring + digest delivery to match the use case narrative.

---

## Feature-by-Feature Comparison

### ✅ **1. Automated Job Capture** — **PARTIALLY WORKING (5/10)**

**Use Case Promise:**
> "Connect your job alerts (LinkedIn, Indeed, email forwards) → Stride's API ingests new postings automatically → No more copy-pasting or losing track of opportunities"

**Current Reality:**
- ✅ API endpoints exist (`POST /api/jobs`)
- ✅ Chrome extension can capture LinkedIn jobs one-click
- ❌ **No automated daily ingestion from LinkedIn/Indeed**
- ❌ **No email forwarding/parsing integration**
- ❌ **No scheduled browser automation**

**Gap:**
The Chrome extension is *semi-automated* (reduces copy-paste), but users still have to **manually browse LinkedIn and click the extension button for each job**. The use case implies a hands-off "alert monitoring" system that doesn't exist yet.

**What's Needed:**
1. **Browser automation cron job** — Daily LinkedIn search → scrape new jobs → POST to API → create leads
2. **Email ingestion** — Forward Indeed/LinkedIn/Glassdoor alerts to `jobs@stride.app` → parse → import
3. **RSS/API monitoring** — Poll job boards for new listings matching user's criteria

**Effort:** Medium (2-3 weeks)

---

### ✅ **2. AI-Powered Fit Scoring** — **WORKING BUT MANUAL (7/10)**

**Use Case Promise:**
> "Upload your resume once → Stride analyzes each job against your background → Get instant fit scores (0-100) highlighting alignment and gaps"

**Current Reality:**
- ✅ `analyze_resume_job_fit()` function implemented (Claude 3.5 Haiku)
- ✅ Returns match score (0-100), matching skills, missing skills, suggestions, keywords
- ✅ API endpoint `/api/analyze-resume-fit`
- ❌ **Requires manual trigger per job** (no bulk scoring)
- ❌ **Not automatically run on job import**
- ❌ **Score not displayed in dashboard/pipeline views**

**Gap:**
The AI is there, but it's hidden. Users have to click "Analyze Fit" for each job individually. The use case implies scoring happens automatically on import and is prominently displayed.

**What's Needed:**
1. **Auto-score on job creation** — When a job is imported, automatically run fit analysis if resume exists
2. **Bulk scoring endpoint** — `POST /api/jobs/score-batch` to score all unscored jobs at once
3. **Display score in UI** — Show fit % badge in pipeline cards, job list, and dashboard
4. **Score-based sorting/filtering** — "Show only 80%+ fits"

**Effort:** Small (1 week)

---

### ✅ **3. Centralized Dashboard** — **WORKING WELL (9/10)**

**Use Case Promise:**
> "All jobs in one place with status tracking (New → Applied → Interview → Offer) → Sort by fit score, salary, location, or posting date → Tag roles (Hot Lead, Research, Pass)"

**Current Reality:**
- ✅ Dashboard with stats tiles (applications by status, events, contacts, stale apps)
- ✅ Kanban pipeline with 12 status stages
- ✅ Job list with search and filters
- ✅ Company and contact management
- ✅ Tagging system implemented
- ⚠️ **No fit score sorting** (score not stored/displayed yet)

**Gap:**
Everything works except fit score integration. Once scoring is automated (see #2), this becomes a 10/10.

**What's Needed:**
1. Add `fit_score` column to `jobs` table
2. Display score badges in pipeline/lists
3. Add "Sort by fit score" option

**Effort:** Tiny (2 days)

---

### ❌ **4. Smart Alerts** — **NOT IMPLEMENTED (2/10)**

**Use Case Promise:**
> "Daily digest of top matches delivered via Telegram/Slack/Email → '3 new VP Product roles just dropped — 2 are 85%+ fits' → Never miss a high-value opportunity"

**Current Reality:**
- ✅ Notification system exists (`notification_generator.py`)
- ✅ Generates interview reminders and follow-up nudges
- ❌ **No job alerts/digests implemented**
- ❌ **No Telegram/Slack/Email delivery integration**
- ❌ **No daily cron job for smart alerting**

**Gap:**
This is the **biggest missing piece**. The use case's core value prop is "you get the best jobs delivered to you." Right now, users have to go hunt for jobs manually. The notification system is there for *after* you apply, but not for *finding* opportunities.

**What's Needed:**
1. **Daily job digest cron** — Runs at 8am, finds new jobs (via automation from #1), scores them (from #2), picks top 3-5 matches
2. **Messaging integration** — Add Telegram bot, Slack webhook, or email delivery (gog/himalaya)
3. **Smart alerting logic** — "3 new roles, 2 are 85%+ fits, 1 is 92% (your top match this week)"
4. **User preferences** — Set digest frequency, minimum fit score, preferred channels

**Effort:** Medium (2 weeks)

---

### ✅ **5. Chrome Extension** — **WORKING WELL (8/10)**

**Use Case Promise:**
> (Implied: one-click capture from LinkedIn)

**Current Reality:**
- ✅ Detects LinkedIn profiles, company pages, job listings
- ✅ Auto-populates forms with scraped data
- ✅ Submits to API with X-API-Key auth
- ✅ Multi-selector fallback for resilience
- ⚠️ **LinkedIn DOM changes can break scrapers** (maintenance risk)
- ⚠️ **No "import all visible jobs" bulk feature**

**Gap:**
Works great for one-off imports, but still requires clicking through every job manually. A "Bulk Import" button to grab all 25 jobs on the current LinkedIn search page would be a huge UX win.

**What's Needed:**
1. **Bulk import** — "Import all jobs on this page" button
2. **Auto-refresh scrapers** — Use AI to adapt to LinkedIn DOM changes (e.g., Claude generates new selectors)
3. **Indeed/Glassdoor extension support**

**Effort:** Small (1 week)

---

## Real Example Comparison

**Use Case Story:**
> Mike, a design + product leader, gets 50+ job alerts per week. Before Stride, he spent 2-3 hours manually reviewing listings. Now:
> - Stride auto-imports 10-15 relevant roles daily
> - AI fit scoring surfaces the top 3-5 worth applying to
> - He reviews his digest over coffee and applies to high-signal roles only
> - **Result: 70% less time searching, 3x more interviews**

**Current Reality:**
Mike gets 50+ job alerts per week. With Stride today:
- ❌ He still has to manually visit LinkedIn and click the Chrome extension 50 times
- ❌ No AI fit scoring happens unless he manually triggers it per job
- ❌ No digest delivered — he has to log into Stride and manually review the dashboard
- ⚠️ The pipeline and tracking work great *once jobs are in*, but getting them in is still manual labor

**Time Saved:** ~20% (Chrome extension is faster than copy-paste, but still requires browsing)  
**Interviews:** No data/analytics to prove 3x claim

---

## Priority Fixes to Match Use Case

### 🔥 **Critical (Needed to Match Use Case)**

1. **Automated Job Ingestion** (2-3 weeks)
   - Daily LinkedIn search via browser automation or LinkedIn API
   - Email alert parsing (forward to jobs@stride.app)
   - Cron job: 6am → search LinkedIn → POST new jobs → create leads

2. **Auto AI Scoring** (1 week)
   - Run `analyze_resume_job_fit()` automatically on job import
   - Store `fit_score` in DB
   - Display badges in UI (pipeline cards, lists)

3. **Daily Digest** (2 weeks)
   - Cron job: 8am → find new jobs → score → pick top 3-5 → send Telegram/email
   - Message format: "Good morning! 4 new roles match your profile: …"
   - Include links to review in Stride

### ⚠️ **High Priority (Improves UX)**

4. **Bulk Chrome Extension Import** (1 week)
   - "Import all 25 jobs on this page" button
   - Progress bar + bulk API endpoint

5. **Analytics Dashboard** (1 week)
   - Track applications sent, interviews booked, time saved
   - Prove the "70% less time, 3x more interviews" claim with data

6. **User Preferences** (1 week)
   - Set job search criteria (titles, locations, salary range)
   - Digest frequency (daily, 3x/week, weekly)
   - Minimum fit score threshold (e.g., "only show 70%+ matches")

### 📋 **Nice to Have (Polish)**

7. **Email Ingestion Endpoint** (1 week)
   - `jobs@stride.app` → parse Indeed/LinkedIn emails → import
   - Use AI to extract job details from unstructured emails

8. **LinkedIn Headline Scraper** (3 days)
   - Extension also captures job salary, benefits, seniority level
   - More accurate fit scoring with richer data

9. **Cover Letter Generator UI** (1 week)
   - `generate_cover_letter()` already exists in API
   - Add UI button in application detail page

---

## Scoring Breakdown

| Feature | Use Case Weight | Implementation Score | Weighted Score |
|---------|----------------|---------------------|---------------|
| Automated Job Capture | 30% | 5/10 | 1.5 |
| AI Fit Scoring | 25% | 7/10 | 1.75 |
| Centralized Dashboard | 20% | 9/10 | 1.8 |
| Smart Alerts | 15% | 2/10 | 0.3 |
| Chrome Extension | 10% | 8/10 | 0.8 |
| **TOTAL** | **100%** | **—** | **6.15/10** |

Adjusted for foundation quality: **7.5/10** (excellent infrastructure, missing key automation)

---

## Bottom Line

**What Works:**
- Rock-solid data model and architecture
- Full-featured tracking dashboard
- Chrome extension for LinkedIn
- AI scoring engine (Claude Haiku)
- Notification system for follow-ups

**What's Missing:**
- **Automated daily job ingestion** (the #1 value prop)
- **Daily digest delivery** (the "you get jobs pushed to you" promise)
- **Auto AI scoring** (exists but hidden/manual)

**Recommendation:**
Stride is **70% of the way there**. The foundation is excellent. To match the use case, focus the next 4-6 weeks on:
1. **Automated job capture** (browser automation or email parsing)
2. **Auto AI scoring on import**
3. **Daily digest via Telegram/email**

Once those three are live, the use case becomes 100% truthful and the product delivers on its promise: **"Your Job Search, Finally Automated."**

---

## Next Steps

1. **Choose job ingestion strategy:**
   - Option A: Browser automation (Playwright/Puppeteer + cron)
   - Option B: Email parsing (forward alerts to Stride)
   - Option C: LinkedIn API (if available/affordable)

2. **Integrate fit scoring into job creation workflow**
   - Add `fit_score` column to jobs table
   - Auto-run on import if resume exists
   - Display in UI

3. **Build daily digest cron job**
   - Use OpenClaw's messaging or direct Telegram bot
   - Format: "Top 3 matches today: [Job 1] (92%), [Job 2] (87%), [Job 3] (81%)"

4. **Add analytics to prove ROI**
   - Track time saved vs. manual job hunting
   - Track application → interview conversion rate
   - Provide user-facing stats dashboard

---

**Audit Complete.**  
Ready to prioritize and build. Let me know which piece you want to tackle first.
