"""Flask web application for Job Hunt Tracker."""
import os
from datetime import timedelta
from flask import Flask, request
from flask_login import LoginManager

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

    # Session configuration - keep users logged in for 30 days
    is_production = os.environ.get('VERCEL') or os.environ.get('DATABASE_URL')
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
    app.config['SESSION_COOKIE_SECURE'] = bool(is_production)  # HTTPS only in production
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
    app.config['REMEMBER_COOKIE_SECURE'] = bool(is_production)
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB upload limit
    app.config['AI_PARSING_ENABLED'] = bool(os.environ.get('ANTHROPIC_API_KEY'))

    # Database setup - prefer DATABASE_URL for production
    if database_url is None:
        database_url = os.environ.get('DATABASE_URL')

    if database_url:
        db = DatabaseConnection(database_url=database_url)
    else:
        if db_path is None:
            home = os.path.expanduser("~")
            db_dir = os.path.join(home, ".job-hunt-tracker")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "job_hunt.db")
        db = DatabaseConnection(db_path=db_path)

    db.create_tables()
    app.extensions['db'] = db

    # Prevent browsers from caching static files indefinitely
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

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
            return session.query(User).get(int(user_id))
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
            'ghosted': '#6b7280'
        }
        return colors.get(status, '#6b7280')

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
    app.register_blueprint(compare_bp)
    app.register_blueprint(digest_bp)
    app.register_blueprint(reflections_bp)
    app.register_blueprint(feedback_bp)

    return app


def run_server(db_path: str = None, host: str = '127.0.0.1', port: int = 5000, debug: bool = False):
    """Run the Flask development server."""
    app = create_app(db_path)
    app.run(host=host, port=port, debug=debug)
