"""About page route."""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required

bp = Blueprint('about', __name__)

# Newsletter moved to LinkedIn
NEWSLETTER_URL = 'https://www.linkedin.com/newsletters/stride-7423041699884695552'


@bp.route('/about')
def about():
    """About Stride page - the story behind the product."""
    return render_template('about.html')


# Redirect old blog/notes URLs to My Notes
@bp.route('/notes')
@login_required
def notes_redirect():
    """Redirect old /notes blog URL to My Notes."""
    return redirect(url_for('notes.my_notes'))


@bp.route('/notes/<slug>')
@login_required
def note_redirect(slug):
    """Redirect old /notes/<slug> blog URL to My Notes."""
    return redirect(url_for('notes.my_notes'))


@bp.route('/blog')
@login_required
def blog():
    """Redirect old blog URL to My Notes."""
    return redirect(url_for('notes.my_notes'))


@bp.route('/blog/<slug>')
@login_required
def blog_post(slug):
    """Redirect old blog post URLs to My Notes."""
    return redirect(url_for('notes.my_notes'))
