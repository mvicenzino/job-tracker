"""About and Notes routes."""
import os
import re
from flask import Blueprint, render_template, abort, current_app
from flask_login import login_required
from markupsafe import Markup
import markdown

bp = Blueprint('about', __name__)


# =============================================================================
# NEWSLETTER
# =============================================================================
NEWSLETTER_URL = 'https://www.linkedin.com/newsletters/stride-7423041699884695552'


def get_notes_folder():
    """Get the path to the notes content folder."""
    return os.path.join(current_app.root_path, 'content', 'notes')


def parse_frontmatter(content):
    """Parse YAML-like frontmatter from markdown content."""
    frontmatter = {}
    body = content
    
    # Check for frontmatter (content between --- markers)
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            # Parse the frontmatter
            fm_text = parts[1].strip()
            body = parts[2].strip()
            
            for line in fm_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    # Handle boolean values
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    frontmatter[key] = value
    
    return frontmatter, body


def render_markdown(text):
    """Convert markdown text to HTML."""
    if not text:
        return ''
    html = markdown.markdown(text, extensions=['extra', 'smarty', 'fenced_code'])
    return Markup(html)


def load_all_notes():
    """Load all published notes from the content folder."""
    notes = []
    notes_folder = get_notes_folder()
    
    if not os.path.exists(notes_folder):
        return notes
    
    for filename in os.listdir(notes_folder):
        # Skip template and non-markdown files
        if filename.startswith('_') or not filename.endswith('.md'):
            continue
        
        filepath = os.path.join(notes_folder, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            frontmatter, body = parse_frontmatter(content)
            
            # Skip unpublished notes
            if not frontmatter.get('published', False):
                continue
            
            # Use filename as slug if not specified
            slug = frontmatter.get('slug', filename.replace('.md', ''))
            
            notes.append({
                'slug': slug,
                'title': frontmatter.get('title', 'Untitled'),
                'excerpt': frontmatter.get('excerpt', ''),
                'date': frontmatter.get('date', ''),
                'author': frontmatter.get('author', 'Michael Vicenzino'),
                'content': body,
                'filename': filename
            })
        except Exception as e:
            print(f"Error loading note {filename}: {e}")
            continue
    
    # Sort by date (newest first) - simple string sort works for consistent date format
    notes.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return notes


def load_note_by_slug(slug):
    """Load a single note by its slug."""
    notes_folder = get_notes_folder()
    
    if not os.path.exists(notes_folder):
        return None
    
    for filename in os.listdir(notes_folder):
        if filename.startswith('_') or not filename.endswith('.md'):
            continue
        
        filepath = os.path.join(notes_folder, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            frontmatter, body = parse_frontmatter(content)
            
            # Check if this is the right note
            note_slug = frontmatter.get('slug', filename.replace('.md', ''))
            if note_slug != slug:
                continue
            
            # Skip unpublished (unless we found it by direct slug)
            if not frontmatter.get('published', False):
                return None
            
            return {
                'slug': note_slug,
                'title': frontmatter.get('title', 'Untitled'),
                'excerpt': frontmatter.get('excerpt', ''),
                'date': frontmatter.get('date', ''),
                'author': frontmatter.get('author', 'Michael Vicenzino'),
                'content': body,
                'content_html': render_markdown(body)
            }
        except Exception:
            continue
    
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
    posts = load_all_notes()
    return render_template('notes.html', posts=posts, newsletter_url=NEWSLETTER_URL)


@bp.route('/notes/<slug>')
@login_required
def note(slug):
    """Individual note page."""
    post = load_note_by_slug(slug)
    
    if not post:
        abort(404)
    
    return render_template('note.html', post=post)


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
