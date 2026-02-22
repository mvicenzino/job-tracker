"""Authentication routes: register, login, logout."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlparse

from ...models import User

bp = Blueprint('auth', __name__)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('register.html')

        db = current_app.extensions['db']
        session = db.get_session()
        try:
            # Check if user already exists
            existing_user = session.query(User).filter(User.email == email).first()
            if existing_user:
                flash('An account with this email already exists.', 'error')
                return render_template('register.html')

            # Create new user
            user = User(email=email)
            user.set_password(password)
            session.add(user)
            session.commit()

            login_user(user, remember=True)
            flash('Account created successfully!', 'success')
            return redirect(url_for('dashboard.dashboard'))
        finally:
            session.close()

    return render_template('register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        db = current_app.extensions['db']
        session = db.get_session()
        try:
            user = session.query(User).filter(User.email == email).first()

            if user and user.check_password(password):
                login_user(user, remember=True)
                next_page = request.args.get('next')
                # Validate next_page is a safe, same-origin relative URL
                if next_page:
                    parsed = urlparse(next_page)
                    if parsed.netloc or parsed.scheme:
                        next_page = None
                flash('Logged in successfully!', 'success')
                return redirect(next_page or url_for('dashboard.dashboard'))
            else:
                flash('Invalid email or password.', 'error')
        finally:
            session.close()

    return render_template('login.html')


@bp.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('public.landing'))
