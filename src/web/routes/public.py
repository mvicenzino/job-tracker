"""Public routes: landing, privacy, terms, demo."""
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, redirect, url_for, current_app, flash
from flask_login import current_user, login_user

from ...services import JobHuntService
from ...models import ApplicationStatus, EventType, ContactType, User, ChecklistItem, ResumeVersion

bp = Blueprint('public', __name__)


@bp.route('/')
def landing():
    """Landing page for unauthenticated users."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    return render_template('landing.html')


@bp.route('/privacy')
def privacy():
    """Privacy Policy page."""
    return render_template('privacy.html')


@bp.route('/terms')
def terms():
    """Terms of Service page."""
    return render_template('terms.html')


@bp.route('/demo')
def demo():
    """Demo mode - log in as demo user with sample data."""
    from flask import request
    DEMO_EMAIL = 'demo@stride-jobs.com'
    DEMO_PASSWORD = 'demo-user-2024'

    db = current_app.extensions['db']
    session = db.get_session()
    try:
        # Find or create demo user
        demo_user = session.query(User).filter(User.email == DEMO_EMAIL).first()

        if not demo_user:
            demo_user = User(email=DEMO_EMAIL)
            demo_user.set_password(DEMO_PASSWORD)
            demo_user.subscription_tier = 'pro'
            session.add(demo_user)
            session.commit()
            session.refresh(demo_user)

        # Ensure demo user always has Pro tier
        if demo_user.subscription_tier != 'pro':
            demo_user.subscription_tier = 'pro'
            session.commit()

        # Check if demo data needs to be created or refreshed
        service = JobHuntService(session, user_id=demo_user.id)
        existing_apps = service.applications.get_all()
        force_refresh = request.args.get('refresh') == '1'

        if len(existing_apps) == 0 or force_refresh:
            # Clear existing data for fresh demo using raw SQL to avoid ORM cascade issues
            from sqlalchemy import text

            # Delete in correct order respecting foreign key constraints:
            # 1. Events (references contacts)
            # 2. Contacts (references companies)
            # 3. Notes/Checklist items (references applications)
            # 4. Applications (references jobs)
            # 5. Jobs (references companies)
            # 6. Companies
            # 7. Resume versions

            # First: Delete all events for this user (events reference contacts)
            session.execute(text(f"DELETE FROM events WHERE user_id = {demo_user.id}"))

            # Second: Delete all contacts for this user (contacts reference companies)
            session.execute(text(f"DELETE FROM contacts WHERE user_id = {demo_user.id}"))

            # Get company IDs for this user
            company_ids_result = session.execute(text(f"SELECT id FROM companies WHERE user_id = {demo_user.id}"))
            company_ids = [row[0] for row in company_ids_result.fetchall()]

            if company_ids:
                company_ids_str = ','.join(str(cid) for cid in company_ids)

                # Get job IDs that belong to these companies
                job_ids_result = session.execute(text(f"SELECT id FROM jobs WHERE company_id IN ({company_ids_str})"))
                job_ids = [row[0] for row in job_ids_result.fetchall()]

                if job_ids:
                    job_ids_str = ','.join(str(jid) for jid in job_ids)

                    # Delete things that reference applications
                    session.execute(text(f"DELETE FROM checklist_items WHERE application_id IN (SELECT id FROM applications WHERE job_id IN ({job_ids_str}))"))
                    session.execute(text(f"DELETE FROM notes WHERE application_id IN (SELECT id FROM applications WHERE job_id IN ({job_ids_str}))"))

                    # Delete applications
                    session.execute(text(f"DELETE FROM applications WHERE job_id IN ({job_ids_str})"))

                    # Delete jobs
                    session.execute(text(f"DELETE FROM jobs WHERE id IN ({job_ids_str})"))

                # Delete companies (now safe - no more references)
                session.execute(text(f"DELETE FROM companies WHERE id IN ({company_ids_str})"))

            # Delete resume versions
            session.execute(text(f"DELETE FROM resume_versions WHERE user_id = {demo_user.id}"))
            session.commit()

            # Clear all cached objects from the session to avoid stale references
            session.expire_all()

            # Refresh service after clearing data
            service = JobHuntService(session, user_id=demo_user.id)

            # Create sample companies - diverse industries and sizes
            companies_data = [
                {'name': 'Stripe', 'industry': 'FinTech', 'size': '5000-10000', 'location': 'San Francisco, CA', 'website': 'https://stripe.com', 'description': 'Financial infrastructure for the internet'},
                {'name': 'Notion', 'industry': 'Productivity', 'size': '500-1000', 'location': 'San Francisco, CA', 'website': 'https://notion.so', 'description': 'All-in-one workspace for notes, docs, and collaboration'},
                {'name': 'Figma', 'industry': 'Design Tools', 'size': '1000-2000', 'location': 'San Francisco, CA', 'website': 'https://figma.com', 'description': 'Collaborative interface design tool'},
                {'name': 'Vercel', 'industry': 'Developer Tools', 'size': '200-500', 'location': 'San Francisco, CA', 'website': 'https://vercel.com', 'description': 'Frontend cloud platform'},
                {'name': 'Linear', 'industry': 'Developer Tools', 'size': '50-100', 'location': 'San Francisco, CA', 'website': 'https://linear.app', 'description': 'Modern issue tracking for high-performance teams'},
                {'name': 'Rippling', 'industry': 'HR Tech', 'size': '1000-3000', 'location': 'San Francisco, CA', 'website': 'https://rippling.com', 'description': 'Employee management platform'},
                {'name': 'Anthropic', 'industry': 'AI/ML', 'size': '500-1000', 'location': 'San Francisco, CA', 'website': 'https://anthropic.com', 'description': 'AI safety and research company'},
                {'name': 'Databricks', 'industry': 'Data & Analytics', 'size': '5000-10000', 'location': 'San Francisco, CA', 'website': 'https://databricks.com', 'description': 'Unified analytics platform'},
                {'name': 'Retool', 'industry': 'Developer Tools', 'size': '200-500', 'location': 'San Francisco, CA', 'website': 'https://retool.com', 'description': 'Build internal tools fast'},
                {'name': 'Ramp', 'industry': 'FinTech', 'size': '500-1000', 'location': 'New York, NY', 'website': 'https://ramp.com', 'description': 'Corporate card and spend management'},
                {'name': 'Plaid', 'industry': 'FinTech', 'size': '1000-2000', 'location': 'San Francisco, CA', 'website': 'https://plaid.com', 'description': 'Financial data connectivity'},
                {'name': 'Mercury', 'industry': 'FinTech', 'size': '200-500', 'location': 'San Francisco, CA', 'website': 'https://mercury.com', 'description': 'Banking for startups'},
                {'name': 'Airtable', 'industry': 'Productivity', 'size': '500-1000', 'location': 'San Francisco, CA', 'website': 'https://airtable.com', 'description': 'Low-code platform for building apps'},
                {'name': 'Webflow', 'industry': 'Design Tools', 'size': '500-1000', 'location': 'San Francisco, CA', 'website': 'https://webflow.com', 'description': 'Visual web development platform'},
                {'name': 'Scale AI', 'industry': 'AI/ML', 'size': '500-1000', 'location': 'San Francisco, CA', 'website': 'https://scale.com', 'description': 'Data platform for AI'},
                {'name': 'McKinsey & Company', 'industry': 'Management Consulting', 'size': '10000+', 'location': 'New York, NY', 'website': 'https://mckinsey.com', 'description': 'Global management consulting firm'},
                {'name': 'Deloitte Digital', 'industry': 'Technology Consulting', 'size': '10000+', 'location': 'New York, NY', 'website': 'https://deloittedigital.com', 'description': 'Digital transformation consulting'},
                {'name': 'Bain & Company', 'industry': 'Management Consulting', 'size': '10000+', 'location': 'Boston, MA', 'website': 'https://bain.com', 'description': 'Strategy consulting firm'},
                {'name': 'Accenture', 'industry': 'Technology Consulting', 'size': '10000+', 'location': 'Chicago, IL', 'website': 'https://accenture.com', 'description': 'Professional services and digital transformation'},
            ]

            companies = []
            for data in companies_data:
                company = service.add_company(**data)
                companies.append(company)

            # Create jobs with realistic titles, compensation, and descriptions
            jobs_data = [
                # Active opportunities - various stages
                {'company': companies[0], 'title': 'Senior Software Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 200000, 'salary_max': 280000, 'source': 'Referral',
                 'description': '''We're looking for a Senior Software Engineer to join our Payments team. You'll work on building and scaling our payment infrastructure that processes billions of dollars annually.

You will:
- Design, build, and maintain APIs, services, and systems across Stripe's payments stack
- Debug production issues across services and multiple levels of the stack
- Work with engineers across the company to build new features at scale
- Improve engineering standards, tooling, and processes

Requirements:
- 5+ years of software engineering experience
- Strong proficiency in at least one programming language (we use Ruby, Go, and Java)
- Experience with distributed systems and microservices architecture
- Excellent problem-solving and debugging skills
- Experience with databases (PostgreSQL, Redis) and message queues
- Strong communication skills and ability to work cross-functionally

Nice to have:
- Experience with payment systems or financial technology
- Experience with Kubernetes and cloud infrastructure (AWS/GCP)
- Familiarity with PCI compliance requirements'''},

                {'company': companies[1], 'title': 'Staff Engineer, Platform', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 220000, 'salary_max': 300000, 'source': 'LinkedIn',
                 'description': '''Notion is looking for a Staff Engineer to lead our Platform team. You'll architect and build the foundational systems that power Notion for millions of users.

Responsibilities:
- Lead technical design and architecture for platform infrastructure
- Mentor and grow a team of engineers
- Drive technical decisions that impact the entire engineering organization
- Collaborate with product teams to enable new features and capabilities
- Optimize performance and reliability at scale

Requirements:
- 8+ years of software engineering experience with 3+ years in a senior/staff role
- Deep experience with TypeScript/JavaScript and Node.js
- Strong background in distributed systems and database design
- Experience leading technical projects across multiple teams
- Excellent written and verbal communication skills

Technologies we use: TypeScript, React, Node.js, PostgreSQL, Redis, AWS'''},

                {'company': companies[2], 'title': 'Senior Frontend Engineer', 'location': 'Remote', 'remote_type': 'remote', 'salary_min': 180000, 'salary_max': 250000, 'source': 'Company Website',
                 'description': '''Join Figma as a Senior Frontend Engineer and help us build the future of design tools. You'll work on our web-based editor used by millions of designers worldwide.

What you'll do:
- Build new features for our collaborative design tool
- Optimize performance for complex canvas rendering
- Work closely with designers and product managers
- Contribute to our design system and component library

Requirements:
- 5+ years of frontend development experience
- Expert-level JavaScript/TypeScript skills
- Experience with React and modern frontend tooling
- Understanding of browser rendering and performance optimization
- Experience with WebGL or Canvas APIs is a plus
- Strong eye for design and attention to detail'''},

                {'company': companies[3], 'title': 'Software Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 170000, 'salary_max': 230000, 'source': 'LinkedIn',
                 'description': '''Vercel is hiring Software Engineers to work on our frontend cloud platform. Help us make the web faster for everyone.

You will:
- Build and improve our deployment and hosting infrastructure
- Work on developer tools and CLI
- Contribute to Next.js and our open source projects
- Optimize edge computing and CDN systems

Requirements:
- 3+ years of software engineering experience
- Strong JavaScript/TypeScript skills
- Experience with React and Next.js
- Understanding of web performance and CDN architecture
- Passion for developer experience and open source'''},

                {'company': companies[4], 'title': 'Founding Engineer', 'location': 'San Francisco, CA', 'remote_type': 'onsite', 'salary_min': 180000, 'salary_max': 240000, 'source': 'Referral',
                 'description': '''Linear is looking for a Founding Engineer to help build the future of issue tracking. Join our small, high-impact team.

What you'll do:
- Own entire features from design to implementation
- Shape the technical direction of the product
- Work directly with founders and early customers
- Build a product that developers love

Requirements:
- 4+ years of software engineering experience
- Full-stack development skills (React, Node.js, PostgreSQL)
- Strong product sense and attention to detail
- Ability to move fast and ship quality code
- Startup experience preferred'''},

                {'company': companies[5], 'title': 'Senior Backend Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 190000, 'salary_max': 260000, 'source': 'Recruiter',
                 'description': '''Rippling is hiring Senior Backend Engineers to build our unified HR platform.

Responsibilities:
- Design and build scalable backend services
- Work on integrations with payroll, benefits, and HR systems
- Improve system reliability and performance
- Mentor junior engineers

Requirements:
- 5+ years of backend engineering experience
- Strong Python or Go skills
- Experience with PostgreSQL and distributed systems
- Understanding of API design and microservices
- Experience with AWS infrastructure'''},

                {'company': companies[6], 'title': 'Research Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 250000, 'salary_max': 350000, 'source': 'Company Website',
                 'description': '''Anthropic is seeking Research Engineers to work on AI safety and capabilities research. Help us build AI systems that are safe, beneficial, and understandable.

What you'll do:
- Implement and iterate on ML experiments
- Build infrastructure for training large language models
- Collaborate with researchers on novel AI techniques
- Contribute to our understanding of AI alignment

Requirements:
- MS/PhD in CS, ML, or related field (or equivalent experience)
- Strong programming skills in Python
- Experience with PyTorch or JAX
- Understanding of modern ML architectures (transformers, etc.)
- Experience training large models is a plus
- Interest in AI safety and alignment research'''},

                {'company': companies[7], 'title': 'Staff Data Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 230000, 'salary_max': 320000, 'source': 'LinkedIn',
                 'description': '''Databricks is hiring a Staff Data Engineer to build our data platform. Work on cutting-edge data and ML infrastructure.

You will:
- Design and build data pipelines at massive scale
- Work on Apache Spark and Delta Lake
- Optimize query performance and data processing
- Lead technical projects and mentor engineers

Requirements:
- 7+ years of data engineering experience
- Expert-level SQL and Python skills
- Deep experience with Spark and distributed computing
- Experience with cloud data platforms (AWS, Azure, GCP)
- Strong understanding of data modeling and warehousing'''},

                {'company': companies[8], 'title': 'Full Stack Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 175000, 'salary_max': 240000, 'source': 'AngelList',
                 'description': '''Retool is looking for Full Stack Engineers to help us build internal tools faster.

What you'll do:
- Build features for our low-code platform
- Work across the stack from React frontend to Node.js backend
- Improve our component library and integrations
- Help customers build better internal tools

Requirements:
- 3+ years of full-stack experience
- Strong React and TypeScript skills
- Node.js and PostgreSQL experience
- Interest in developer tools and productivity'''},

                {'company': companies[9], 'title': 'Senior Software Engineer', 'location': 'New York, NY', 'remote_type': 'hybrid', 'salary_min': 200000, 'salary_max': 270000, 'source': 'Referral',
                 'description': '''Ramp is hiring Senior Software Engineers to build the future of corporate spend management.

You will:
- Build features for our corporate card and expense platform
- Work on real-time transaction processing
- Improve our accounting integrations
- Scale systems handling billions in transactions

Requirements:
- 5+ years of software engineering experience
- Strong Python or Go skills
- Experience with PostgreSQL and Redis
- Understanding of financial systems is a plus'''},

                # Saved for later / researching
                {'company': companies[10], 'title': 'Staff Engineer, Payments', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 240000, 'salary_max': 330000, 'source': 'LinkedIn'},
                {'company': companies[11], 'title': 'Senior Software Engineer', 'location': 'Remote', 'remote_type': 'remote', 'salary_min': 180000, 'salary_max': 250000, 'source': 'Company Website'},
                {'company': companies[12], 'title': 'Platform Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 185000, 'salary_max': 255000, 'source': 'Indeed'},
                {'company': companies[13], 'title': 'Senior Full Stack Engineer', 'location': 'Remote', 'remote_type': 'remote', 'salary_min': 175000, 'salary_max': 245000, 'source': 'LinkedIn'},
                {'company': companies[14], 'title': 'ML Platform Engineer', 'location': 'San Francisco, CA', 'remote_type': 'hybrid', 'salary_min': 210000, 'salary_max': 290000, 'source': 'Recruiter'},
                # Consulting opportunities
                {'company': companies[15], 'title': 'Digital Strategy Engagement', 'location': 'New York, NY', 'remote_type': 'hybrid', 'salary_min': 500000, 'salary_max': 800000, 'source': 'Referral',
                 'description': 'Lead digital transformation strategy for a Fortune 100 retailer. 12-week engagement covering technology roadmap, organizational change management, and implementation planning.'},
                {'company': companies[16], 'title': 'Cloud Migration Assessment', 'location': 'Remote', 'remote_type': 'remote', 'salary_min': 300000, 'salary_max': 450000, 'source': 'Networking',
                 'description': 'Assess and plan enterprise cloud migration for a mid-market financial services firm. Deliverables include architecture review, cost-benefit analysis, and migration roadmap.'},
                {'company': companies[17], 'title': 'Growth Strategy Project', 'location': 'Boston, MA', 'remote_type': 'onsite', 'salary_min': 600000, 'salary_max': 900000, 'source': 'Company Website',
                 'description': 'Help a PE-backed SaaS company develop go-to-market strategy for international expansion. 8-week engagement with potential for follow-on work.'},
                {'company': companies[18], 'title': 'AI Readiness Workshop Series', 'location': 'Chicago, IL', 'remote_type': 'hybrid', 'salary_min': 150000, 'salary_max': 250000, 'source': 'LinkedIn',
                 'description': 'Design and deliver AI readiness workshops for C-suite executives at a healthcare conglomerate. 4-session series over 6 weeks.'},
            ]

            jobs = []
            for data in jobs_data:
                company = data.pop('company')
                job = service.jobs.create(company_id=company.id, **data)
                jobs.append(job)

            # Create applications with realistic pipeline distribution
            # Shows a healthy job search with activity at every stage
            application_configs = [
                # OFFER stage - exciting! (analyzed and great fit)
                {'job_idx': 0, 'status': ApplicationStatus.OFFER, 'days_ago': 25, 'excitement': 5, 'fit_score': 92},
                # NEGOTIATING - actively discussing terms
                {'job_idx': 6, 'status': ApplicationStatus.NEGOTIATING, 'days_ago': 30, 'excitement': 5, 'fit_score': 87},
                # FINAL_ROUND - close to finish line
                {'job_idx': 1, 'status': ApplicationStatus.FINAL_ROUND, 'days_ago': 21, 'excitement': 4, 'fit_score': 78},
                {'job_idx': 7, 'status': ApplicationStatus.FINAL_ROUND, 'days_ago': 18, 'excitement': 4, 'fit_score': 84},
                # INTERVIEWING - in the thick of it
                {'job_idx': 2, 'status': ApplicationStatus.INTERVIEWING, 'days_ago': 14, 'excitement': 4, 'fit_score': 72},
                {'job_idx': 4, 'status': ApplicationStatus.INTERVIEWING, 'days_ago': 12, 'excitement': 5, 'fit_score': 85},
                {'job_idx': 9, 'status': ApplicationStatus.INTERVIEWING, 'days_ago': 10, 'excitement': 3, 'fit_score': 68},
                # SCREENING - early conversations
                {'job_idx': 3, 'status': ApplicationStatus.SCREENING, 'days_ago': 8, 'excitement': 3, 'fit_score': 75},
                {'job_idx': 5, 'status': ApplicationStatus.SCREENING, 'days_ago': 6, 'excitement': 4},  # Not yet analyzed
                # APPLIED - waiting to hear back (some stale for "needs attention")
                {'job_idx': 8, 'status': ApplicationStatus.APPLIED, 'days_ago': 18, 'excitement': 3, 'fit_score': 58},  # Lower fit, stale
                # PREPARING - working on application
                {'job_idx': 10, 'status': ApplicationStatus.PREPARING, 'days_ago': 2, 'excitement': 4},  # Not yet analyzed
                {'job_idx': 14, 'status': ApplicationStatus.PREPARING, 'days_ago': 1, 'excitement': 5, 'fit_score': 81},
                # INTERESTED - saved for later (mostly not analyzed yet)
                {'job_idx': 11, 'status': ApplicationStatus.INTERESTED, 'days_ago': 5, 'excitement': 3},
                {'job_idx': 12, 'status': ApplicationStatus.INTERESTED, 'days_ago': 3, 'excitement': 3},
                {'job_idx': 13, 'status': ApplicationStatus.INTERESTED, 'days_ago': 1, 'excitement': 4},
            ]

            apps = []
            for config in application_configs:
                job = jobs[config['job_idx']]
                app = service.apply_to_job(job_id=job.id)
                service.update_application_status(app.id, config['status'])
                app.date_applied = date.today() - timedelta(days=config['days_ago'])
                app.excitement_level = config['excitement']
                if config.get('fit_score'):
                    app.fit_score = config['fit_score']
                    # Also set on the Job so pipeline/job list badges render
                    job.fit_score = config['fit_score']
                apps.append(app)

            # Set offer details on the offer
            apps[0].offered_salary = 260000
            apps[0].offered_bonus = 50000
            apps[0].offered_equity = '0.05% over 4 years'

            # Create sample contacts - networking is key!
            contacts_data = [
                {'name': 'Alex Rivera', 'company_name': 'Stripe', 'title': 'Engineering Manager', 'contact_type': ContactType.HIRING_MANAGER, 'email': 'alex.r@stripe.com', 'linkedin_url': 'https://linkedin.com/in/alexrivera', 'notes': 'Met at SF Tech Meetup. Very responsive.'},
                {'name': 'Jordan Lee', 'company_name': 'Notion', 'title': 'Staff Engineer', 'contact_type': ContactType.REFERRAL, 'email': 'jordan.l@notion.so', 'linkedin_url': 'https://linkedin.com/in/jordanlee', 'notes': 'Former colleague from Dropbox. Offered to refer me.'},
                {'name': 'Sam Chen', 'company_name': 'Figma', 'title': 'Technical Recruiter', 'contact_type': ContactType.RECRUITER, 'email': 'sam.c@figma.com', 'linkedin_url': 'https://linkedin.com/in/samchen', 'notes': 'Very helpful, keeps me updated on process.'},
                {'name': 'Taylor Kim', 'company_name': 'Linear', 'title': 'Co-founder', 'contact_type': ContactType.HIRING_MANAGER, 'email': 'taylor@linear.app', 'linkedin_url': 'https://linkedin.com/in/taylorkim', 'notes': 'Reached out after seeing my open source work.'},
                {'name': 'Morgan Walsh', 'company_name': 'Anthropic', 'title': 'Research Lead', 'contact_type': ContactType.HIRING_MANAGER, 'email': 'morgan.w@anthropic.com', 'linkedin_url': 'https://linkedin.com/in/morganwalsh', 'notes': 'Had great chat about AI safety research.'},
                {'name': 'Casey Park', 'company_name': 'Ramp', 'title': 'Senior Recruiter', 'contact_type': ContactType.RECRUITER, 'email': 'casey.p@ramp.com', 'linkedin_url': 'https://linkedin.com/in/caseypark', 'notes': 'Proactive about scheduling and updates.'},
                {'name': 'Jamie Torres', 'company_name': 'Databricks', 'title': 'Principal Engineer', 'contact_type': ContactType.EMPLOYEE, 'email': 'jamie.t@databricks.com', 'linkedin_url': 'https://linkedin.com/in/jamietorres', 'notes': 'Coffee chat to learn about the team.'},
                {'name': 'Riley Nguyen', 'company_name': 'Vercel', 'title': 'Engineering Lead', 'contact_type': ContactType.HIRING_MANAGER, 'email': 'riley.n@vercel.com', 'linkedin_url': 'https://linkedin.com/in/rileynguyen', 'notes': 'Discussed Next.js and edge computing.'},
            ]

            created_contacts = []
            for data in contacts_data:
                created_contacts.append(service.add_contact(**data))

            # Set follow-up dates - some overdue for "Needs Attention"
            created_contacts[0].next_followup_date = date.today() - timedelta(days=2)  # Overdue
            created_contacts[0].last_contact_date = date.today() - timedelta(days=9)
            created_contacts[1].next_followup_date = date.today() - timedelta(days=1)  # Overdue
            created_contacts[1].last_contact_date = date.today() - timedelta(days=8)
            created_contacts[2].next_followup_date = date.today()  # Due today
            created_contacts[2].last_contact_date = date.today() - timedelta(days=5)
            created_contacts[3].next_followup_date = date.today() + timedelta(days=2)  # Upcoming
            created_contacts[3].last_contact_date = date.today() - timedelta(days=3)
            created_contacts[4].next_followup_date = date.today() - timedelta(days=3)  # Overdue
            created_contacts[4].last_contact_date = date.today() - timedelta(days=10)
            created_contacts[5].next_followup_date = date.today() + timedelta(days=1)  # Tomorrow
            created_contacts[5].last_contact_date = date.today() - timedelta(days=4)
            created_contacts[6].next_followup_date = date.today() - timedelta(days=1)  # Overdue
            created_contacts[6].last_contact_date = date.today() - timedelta(days=7)

            # Create sample events - busy interview schedule!
            today_base = datetime.now().replace(minute=0, second=0, microsecond=0)
            events_data = [
                # TODAY - action-packed day
                {'title': 'Recruiter Sync - Ramp', 'event_type': EventType.PHONE_SCREEN, 'start_time': today_base.replace(hour=9), 'meeting_link': 'https://zoom.us/j/ramp123', 'prep_notes': 'Discuss timeline and next steps. Ask about team culture.'},
                {'title': 'System Design - Stripe', 'event_type': EventType.TECHNICAL_INTERVIEW, 'start_time': today_base.replace(hour=11), 'meeting_link': 'https://meet.google.com/stripe-design', 'prep_notes': 'Design a payment processing system. Review distributed systems concepts.'},
                {'title': 'Coffee Chat - Jamie (Databricks)', 'event_type': EventType.COFFEE_CHAT, 'start_time': today_base.replace(hour=12, minute=30), 'location': 'Sightglass Coffee, SOMA'},
                {'title': 'Hiring Manager Call - Anthropic', 'event_type': EventType.VIDEO_INTERVIEW, 'start_time': today_base.replace(hour=14), 'meeting_link': 'https://meet.google.com/anthropic-hm', 'prep_notes': 'Discuss research interests and team fit. Bring questions about safety research.'},
                {'title': 'Take-Home Due - Linear', 'event_type': EventType.APPLICATION_DEADLINE, 'start_time': today_base.replace(hour=18), 'prep_notes': 'Submit React component library challenge. Polish documentation.'},

                # TOMORROW
                {'title': 'Final Round Prep', 'event_type': EventType.REMINDER, 'start_time': today_base + timedelta(days=1, hours=9), 'prep_notes': 'Review Notion architecture and prepare STAR stories.'},
                {'title': 'Panel Interview - Notion', 'event_type': EventType.PANEL_INTERVIEW, 'start_time': today_base + timedelta(days=1, hours=10), 'meeting_link': 'https://zoom.us/j/notion-panel', 'prep_notes': '4 interviewers: 2 engineers, PM, design. Focus on collaboration stories.'},
                {'title': 'Networking Event - SF Tech', 'event_type': EventType.NETWORKING_EVENT, 'start_time': today_base + timedelta(days=1, hours=18), 'location': 'The Pearl, SOMA', 'prep_notes': 'Bring business cards. Target: meet 3 new connections.'},

                # THIS WEEK
                {'title': 'Offer Discussion - Stripe', 'event_type': EventType.OFFER_CALL, 'start_time': today_base + timedelta(days=2, hours=11), 'meeting_link': 'https://meet.google.com/stripe-offer', 'prep_notes': 'Review comp package. Prepare counter-offer talking points.'},
                {'title': 'Technical Deep Dive - Figma', 'event_type': EventType.TECHNICAL_INTERVIEW, 'start_time': today_base + timedelta(days=2, hours=14), 'meeting_link': 'https://zoom.us/j/figma-tech', 'prep_notes': 'Focus on frontend architecture and performance.'},
                {'title': 'Follow up - Alex (Stripe)', 'event_type': EventType.FOLLOW_UP, 'start_time': today_base + timedelta(days=3, hours=10), 'prep_notes': 'Send thank you note and ask about timeline.'},
                {'title': 'Final Round - Databricks', 'event_type': EventType.ONSITE_INTERVIEW, 'start_time': today_base + timedelta(days=4, hours=9), 'location': 'Databricks HQ, 160 Spear St', 'prep_notes': 'Full day: 5 rounds. Wear comfortable shoes!'},
                {'title': 'Culture Chat - Vercel', 'event_type': EventType.BEHAVIORAL_INTERVIEW, 'start_time': today_base + timedelta(days=5, hours=15), 'meeting_link': 'https://zoom.us/j/vercel-culture'},

                # NEXT WEEK
                {'title': 'Negotiation Call - Anthropic', 'event_type': EventType.NEGOTIATION_CALL, 'start_time': today_base + timedelta(days=7, hours=10), 'prep_notes': 'Discuss equity and start date flexibility.'},
                {'title': 'Meet the Team - Linear', 'event_type': EventType.PANEL_INTERVIEW, 'start_time': today_base + timedelta(days=8, hours=11), 'meeting_link': 'https://zoom.us/j/linear-team'},
            ]

            for data in events_data:
                service.schedule_event(**data)

            # Create sample resume versions for AI analysis demo
            resume_general = ResumeVersion(
                user_id=demo_user.id,
                name='General',
                content='''ALEX CHEN
Senior Software Engineer | San Francisco, CA
alex.chen@email.com | linkedin.com/in/alexchen | github.com/alexchen

SUMMARY
Senior Software Engineer with 7+ years of experience building scalable web applications and distributed systems. Passionate about clean code, developer experience, and mentoring teams. Strong background in full-stack development with expertise in React, Node.js, and cloud infrastructure.

EXPERIENCE

Senior Software Engineer | TechCorp Inc. | 2021 - Present
- Led development of real-time analytics platform processing 10M+ events daily
- Architected microservices migration reducing deployment time by 60%
- Mentored team of 5 junior engineers, improving team velocity by 40%
- Implemented CI/CD pipelines using GitHub Actions and Kubernetes
- Technologies: TypeScript, React, Node.js, PostgreSQL, Redis, AWS

Software Engineer | StartupXYZ | 2019 - 2021
- Built customer-facing dashboard serving 50K+ daily active users
- Designed RESTful APIs and GraphQL services
- Reduced page load time by 45% through performance optimization
- Collaborated with product team to ship features on tight deadlines
- Technologies: JavaScript, React, Python, Django, PostgreSQL

Software Engineer | WebAgency | 2017 - 2019
- Developed responsive web applications for Fortune 500 clients
- Created reusable component libraries used across 10+ projects
- Participated in code reviews and established coding standards
- Technologies: JavaScript, React, Vue.js, Node.js, MongoDB

EDUCATION
B.S. Computer Science | UC Berkeley | 2017

SKILLS
Languages: TypeScript, JavaScript, Python, Go, SQL
Frontend: React, Next.js, Vue.js, HTML/CSS, Tailwind
Backend: Node.js, Express, Django, FastAPI, GraphQL
Databases: PostgreSQL, MongoDB, Redis, DynamoDB
Cloud/DevOps: AWS, GCP, Docker, Kubernetes, Terraform
Tools: Git, GitHub Actions, Jest, Cypress'''
            )
            session.add(resume_general)

            resume_technical = ResumeVersion(
                user_id=demo_user.id,
                name='Technical',
                content='''ALEX CHEN
Senior Software Engineer | Distributed Systems & Platform Engineering
San Francisco, CA | alex.chen@email.com | github.com/alexchen

TECHNICAL SUMMARY
Senior engineer specializing in distributed systems, platform infrastructure, and developer tooling. 7+ years building high-throughput systems processing millions of requests. Deep expertise in system design, performance optimization, and technical leadership.

TECHNICAL EXPERIENCE

Senior Software Engineer | TechCorp Inc. | 2021 - Present
Platform & Infrastructure Focus:
- Designed event-driven architecture handling 10M+ daily events with 99.99% uptime
- Built distributed task queue system using Redis and Bull, reducing job latency by 70%
- Implemented database sharding strategy for PostgreSQL, scaling to 100M+ records
- Created internal developer platform reducing service deployment time from days to hours
- Established observability stack (Prometheus, Grafana, Jaeger) for 50+ microservices

Technical Leadership:
- Led architecture review board for company-wide technical decisions
- Authored technical RFCs adopted across engineering organization
- Mentored 5 engineers through promotion to senior level

Software Engineer | StartupXYZ | 2019 - 2021
- Optimized GraphQL resolvers reducing API response time by 60%
- Implemented caching layer with Redis reducing database load by 40%
- Built real-time notification system using WebSockets and Redis Pub/Sub
- Designed idempotent API patterns for payment processing reliability

TECHNICAL SKILLS
Systems: Distributed systems, microservices, event-driven architecture, CQRS
Languages: TypeScript, Go, Python, Rust (learning), SQL
Infrastructure: Kubernetes, Docker, Terraform, AWS (EC2, ECS, Lambda, RDS, SQS)
Databases: PostgreSQL (advanced), Redis, MongoDB, Elasticsearch, DynamoDB
Observability: Prometheus, Grafana, Jaeger, DataDog, PagerDuty
Performance: Profiling, load testing, query optimization, caching strategies

OPEN SOURCE
- Contributor to Node.js ecosystem (Bull, TypeORM)
- Maintainer of redis-toolkit (2K+ GitHub stars)
- Speaker at NodeConf 2023: "Scaling Real-time Systems"

EDUCATION
B.S. Computer Science | UC Berkeley | 2017
Focus: Distributed Systems, Database Systems'''
            )
            session.add(resume_technical)

            resume_leadership = ResumeVersion(
                user_id=demo_user.id,
                name='Leadership',
                content='''ALEX CHEN
Engineering Leader | Building High-Performance Teams
San Francisco, CA | alex.chen@email.com | linkedin.com/in/alexchen

LEADERSHIP PROFILE
Engineering leader with 7+ years of experience, including 3+ years leading teams. Track record of building and scaling engineering teams, driving technical strategy, and delivering complex projects. Passionate about creating environments where engineers do their best work.

LEADERSHIP EXPERIENCE

Senior Software Engineer & Tech Lead | TechCorp Inc. | 2021 - Present

Team Leadership:
- Led team of 8 engineers delivering company's highest-revenue product line
- Implemented agile processes improving sprint velocity by 45%
- Reduced engineer turnover from 25% to 5% through mentorship and growth planning
- Established technical interview process, hiring 12 engineers in 18 months
- Created engineering career ladder adopted company-wide

Strategic Impact:
- Partnered with product leadership to define 2-year technical roadmap
- Led platform modernization initiative saving $500K annually in infrastructure costs
- Drove adoption of TypeScript across organization (20+ services migrated)
- Established engineering metrics and OKR framework for 50-person engineering org

Cross-functional Collaboration:
- Regular presenter to executive leadership on technical strategy
- Collaborated with Sales and Customer Success on enterprise feature requirements
- Worked with Security team on SOC 2 compliance initiatives

Software Engineer | StartupXYZ | 2019 - 2021
- Mentored 3 junior engineers, 2 promoted to mid-level within 18 months
- Led technical discussions and architecture decisions for 5-person team
- Facilitated sprint planning and retrospectives

LEADERSHIP PHILOSOPHY
I believe in servant leadership, creating clarity through documentation, and building psychologically safe teams where engineers can take risks and learn from failures.

SKILLS
Leadership: Team building, mentorship, hiring, performance management, strategic planning
Technical: Full-stack development, system design, architecture, technical writing
Process: Agile/Scrum, OKRs, technical roadmapping, incident management

EDUCATION
B.S. Computer Science | UC Berkeley | 2017'''
            )
            session.add(resume_leadership)

            session.commit()

        # Log in as demo user
        login_user(demo_user, remember=False)
        return redirect(url_for('dashboard.dashboard'))
    except Exception as e:
        session.rollback()
        current_app.logger.exception('Demo setup failed')
        flash('Demo setup failed. Please try again.', 'error')
        return redirect(url_for('public.landing'))
    finally:
        session.close()
