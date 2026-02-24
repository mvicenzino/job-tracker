"""Flask web application for Job Hunt Tracker."""
import os
from datetime import timedelta
from flask import Flask, request, redirect, url_for, flash
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from ..database.connection import DatabaseConnection
from ..models import User

# Stable fallback secret key for development (production should set SECRET_KEY env var)
DEFAULT_SECRET_KEY = 'stride-app-dev-key-change-in-production-abc123xyz'


def create_app(db_path: str = None, database_url: str = None):
    """Create and configure the Flask application."""
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    app.secret_key = os.environ.get('SECRET_KEY', DEFAULT_SECRET_KEY)

    # Enforce SECRET_KEY in production — never use the default on Vercel
    if os.environ.get('VERCEL') and app.secret_key == DEFAULT_SECRET_KEY:
        raise RuntimeError(
            'SECRET_KEY environment variable must be set in production. '
            'Do not use the default development key.'
        )

    # CSRF protection for all forms
    csrf = CSRFProtect(app)

    # Session configuration - keep users logged in for 30 days
    is_production = os.environ.get('VERCEL') or os.environ.get('DATABASE_URL')
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
    app.config['SESSION_COOKIE_SECURE'] = bool(is_production)  # HTTPS only in production
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
    app.config['REMEMBER_COOKIE_SECURE'] = bool(is_production)
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024  # 3 MB upload limit
    app.config['AI_PARSING_ENABLED'] = bool(os.environ.get('ANTHROPIC_API_KEY'))

    # Database setup - prefer DATABASE_URL for production
    if database_url is None:
        database_url = os.environ.get('DATABASE_URL')

    # Normalize DATABASE_URL for SQLAlchemy (needs postgresql+psycopg2:// prefix)
    if database_url:
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql+psycopg2://', 1)
        elif database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)

    if database_url:
        db = DatabaseConnection(database_url=database_url)
    else:
        if db_path is None:
            home = os.path.expanduser("~")
            db_dir = os.path.join(home, ".job-hunt-tracker")
            try:
                os.makedirs(db_dir, exist_ok=True)
            except OSError:
                # Read-only filesystem (e.g. Vercel) — fall back to /tmp
                db_dir = os.path.join("/tmp", ".job-hunt-tracker")
                os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "job_hunt.db")
        db = DatabaseConnection(db_path=db_path)

    db.create_tables()
    app.extensions['db'] = db

    # Prevent browsers from caching static files indefinitely
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    @app.errorhandler(413)
    def request_entity_too_large(error):
        flash('File too large. Please choose a smaller file (under 2MB).', 'error')
        return redirect(url_for('settings.settings'))

    @app.after_request
    def add_cache_headers(response):
        if 'static' in response.headers.get('Content-Type', '') or request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response

    @app.context_processor
    def inject_ai_config():
        return {'ai_parsing_enabled': app.config.get('AI_PARSING_ENABLED', False)}

    @app.context_processor
    def inject_followup_count():
        """Inject overdue followups count for nav badge."""
        from flask_login import current_user
        try:
            if current_user.is_authenticated:
                from ..repositories import ContactRepository
                session = db.get_session()
                try:
                    contacts_repo = ContactRepository(session, user_id=current_user.id)
                    overdue = contacts_repo.get_needing_followup()
                    return {'overdue_followups_count': len(overdue)}
                finally:
                    session.close()
        except Exception:
            pass  # Fail silently - badge is non-critical
        return {'overdue_followups_count': 0}

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please sign in to continue.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login."""
        session = db.get_session()
        try:
            user = session.query(User).get(int(user_id))
            if user:
                # Eagerly load all attributes to avoid issues with detached session
                session.expire_on_commit = False
                # Access key attributes to ensure they're loaded
                _ = user.id, user.email, user.is_active, user.subscription_tier, user.subscription_started_at
            return user
        except Exception as e:
            # Log error but don't crash - user will be redirected to login
            print(f"Error loading user {user_id}: {e}")
            return None
        finally:
            session.close()

    # Template filters
    @app.template_filter('status_color')
    def status_color(status):
        colors = {
            'interested': '#6b7280',
            'preparing': '#8b5cf6',
            'applied': '#3b82f6',
            'screening': '#06b6d4',
            'interviewing': '#f59e0b',
            'final_round': '#f97316',
            'offer': '#22c55e',
            'negotiating': '#14b8a6',
            'accepted': '#10b981',
            'rejected': '#ef4444',
            'withdrawn': '#9ca3af',
            'ghosted': '#6b7280',
            'archived': '#d1d5db'
        }
        return colors.get(status, '#6b7280')

    @app.template_filter('status_description')
    def status_description(status):
        descriptions = {
            'interested': 'Saved for later - you want to apply',
            'preparing': 'Working on resume, cover letter, or application',
            'applied': 'Application submitted - waiting to hear back',
            'screening': 'Recruiter call or phone screen scheduled/completed',
            'interviewing': 'In the interview process',
            'final_round': 'Final interviews with team or leadership',
            'offer': 'Received an offer - reviewing terms',
            'negotiating': 'Discussing salary, benefits, or start date',
            'accepted': 'You accepted the offer!',
            'rejected': 'Company declined to move forward',
            'withdrawn': 'You decided not to continue',
            'ghosted': 'No response after 2+ weeks',
            'archived': 'Hidden from view - can be restored anytime'
        }
        return descriptions.get(status, '')

    @app.template_filter('status_phase')
    def status_phase(status):
        phases = {
            'interested': 'Exploring',
            'preparing': 'Exploring',
            'applied': 'Active',
            'screening': 'Interviewing',
            'interviewing': 'Interviewing',
            'final_round': 'Interviewing',
            'offer': 'Decision',
            'negotiating': 'Decision',
            'accepted': 'Closed',
            'rejected': 'Closed',
            'withdrawn': 'Closed',
            'ghosted': 'Closed',
            'archived': 'Archived'
        }
        return phases.get(status, '')

    @app.template_filter('event_type_icon')
    def event_type_icon(event_type):
        icons = {
            'phone_screen': '📞',
            'video_interview': '💻',
            'onsite_interview': '🏢',
            'technical_interview': '⚙️',
            'behavioral_interview': '💬',
            'panel_interview': '👥',
            'coffee_chat': '☕',
            'networking_event': '🤝',
            'career_fair': '🎪',
            'follow_up': '📧',
            'offer_call': '🎉',
            'negotiation_call': '💰',
            'application_deadline': '⏰',
            'task_deadline': '📋',
            'reminder': '🔔',
            'other': '📌'
        }
        return icons.get(event_type, '📌')

    @app.context_processor
    def inject_usage_data():
        """Inject subscription tier and usage data for all templates."""
        from flask_login import current_user
        try:
            if current_user.is_authenticated:
                from ..services.usage_tracker import UsageTracker
                session = db.get_session()
                try:
                    from ..models import User
                    user = session.query(User).get(current_user.id)
                    if user:
                        tracker = UsageTracker(user, session)
                        usage = tracker.get_usage_summary()
                        is_pro = user.is_pro
                        session.commit()  # persist any month-reset changes
                        return {
                            'user_tier': user.subscription_tier or 'free',
                            'is_pro': is_pro,
                            'usage_data': usage,
                        }
                finally:
                    session.close()
        except Exception:
            pass
        return {'user_tier': 'free', 'is_pro': False, 'usage_data': {}}

    @app.context_processor
    def inject_notification_count():
        """Inject unread notification count for nav badge."""
        from flask_login import current_user
        try:
            if current_user.is_authenticated:
                from ..repositories.notification import NotificationRepository
                session = db.get_session()
                try:
                    notif_repo = NotificationRepository(session)
                    unread = notif_repo.get_unread_count(current_user.id)
                    return {'unread_notifications_count': unread}
                finally:
                    session.close()
        except Exception:
            pass  # Fail silently - badge is non-critical
        return {'unread_notifications_count': 0}

    # Register blueprints
    from .routes.public import bp as public_bp
    from .routes.auth import bp as auth_bp
    from .routes.dashboard import bp as dashboard_bp
    from .routes.applications import bp as applications_bp
    from .routes.companies import bp as companies_bp
    from .routes.jobs import bp as jobs_bp
    from .routes.contacts import bp as contacts_bp
    from .routes.schedule import bp as schedule_bp
    from .routes.settings import bp as settings_bp
    from .routes.api import bp as api_bp
    from .routes.compare import bp as compare_bp
    from .routes.digest import bp as digest_bp
    from .routes.reflections import bp as reflections_bp
    from .routes.feedback import bp as feedback_bp
    from .routes.resumes import bp as resumes_bp
    from .routes.notifications import bp as notifications_bp
    from .routes.about import bp as about_bp
    from .routes.insights import insights_bp
    from .routes.projects import bp as projects_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(companies_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(api_bp)
    csrf.exempt(api_bp)  # API uses API-key auth, not session cookies
    app.register_blueprint(projects_bp)
    csrf.exempt(projects_bp)  # API uses session auth
    app.register_blueprint(compare_bp)
    app.register_blueprint(digest_bp)
    app.register_blueprint(reflections_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(resumes_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(about_bp)
    app.register_blueprint(insights_bp)

    return app


def run_server(db_path: str = None, host: str = '127.0.0.1', port: int = 5000, debug: bool = False):
    """Run the Flask development server."""
    app = create_app(db_path)
    app.run(host=host, port=port, debug=debug)
