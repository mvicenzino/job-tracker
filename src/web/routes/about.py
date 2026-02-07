"""About and Notes routes."""
from flask import Blueprint, render_template, abort
from flask_login import login_required
from markupsafe import Markup
import markdown

bp = Blueprint('about', __name__)


# =============================================================================
# NEWSLETTER
# =============================================================================
NEWSLETTER_URL = 'https://www.linkedin.com/newsletters/stride-7423041699884695552'


# =============================================================================
# NOTES (Blog Posts)
# =============================================================================
# Add new posts here. Format:
# {
#     'slug': 'url-friendly-slug',
#     'title': 'Post Title',
#     'excerpt': 'Short description for the listing page',
#     'date': 'February 7, 2026',
#     'author': 'Michael Vicenzino',
#     'content': '''
#         Markdown content goes here. Supports **bold**, *italic*, 
#         [links](https://example.com), lists, headers, etc.
#     '''
# }
# =============================================================================

NOTES = [
    # Example post (uncomment and modify to add your first post):
    # {
    #     'slug': 'welcome-to-stride',
    #     'title': 'Welcome to Stride',
    #     'excerpt': 'Why I built Stride and what it means for your job search.',
    #     'date': 'February 7, 2026',
    #     'author': 'Michael Vicenzino',
    #     'content': '''
    # ## The Beginning
    # 
    # I built Stride because I was tired of managing my job search in spreadsheets...
    # 
    # ## What's Next
    # 
    # Here's what I'm working on:
    # 
    # - Feature one
    # - Feature two
    # - Feature three
    # 
    # Thanks for being here.
    #     '''
    # },
]


def render_markdown(text):
    """Convert markdown text to HTML."""
    if not text:
        return ''
    # Clean up indentation from multi-line strings
    lines = text.strip().split('\n')
    # Find minimum indentation
    min_indent = float('inf')
    for line in lines:
        if line.strip():
            indent = len(line) - len(line.lstrip())
            min_indent = min(min_indent, indent)
    # Remove common indentation
    if min_indent < float('inf'):
        lines = [line[min_indent:] if len(line) >= min_indent else line for line in lines]
    cleaned = '\n'.join(lines)
    # Convert to HTML
    html = markdown.markdown(cleaned, extensions=['extra', 'smarty'])
    return Markup(html)


def get_note_by_slug(slug):
    """Find a note by its slug."""
    for note in NOTES:
        if note['slug'] == slug:
            return note
    return None


@bp.route('/about')
@login_required
def about():
    """About Stride page - the story behind the product."""
    return render_template('about.html')


@bp.route('/notes')
@login_required
def notes():
    """Notes listing page."""
    # Sort posts by date (newest first) - assumes consistent date format
    posts = sorted(NOTES, key=lambda x: x.get('date', ''), reverse=True)
    return render_template('notes.html', posts=posts, newsletter_url=NEWSLETTER_URL)


@bp.route('/notes/<slug>')
@login_required
def note(slug):
    """Individual note page."""
    post = get_note_by_slug(slug)
    
    if not post:
        abort(404)
    
    # Render markdown content to HTML
    post_data = post.copy()
    post_data['content_html'] = render_markdown(post.get('content', ''))
    
    return render_template('note.html', post=post_data)


# Keep old URLs working (redirect)
@bp.route('/blog')
@login_required
def blog():
    """Redirect old blog URL to notes."""
    from flask import redirect, url_for
    return redirect(url_for('about.notes'))


@bp.route('/blog/<slug>')
@login_required
def blog_post(slug):
    """Redirect old blog post URLs to notes."""
    from flask import redirect, url_for
    return redirect(url_for('about.note', slug=slug))
