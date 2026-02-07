"""About and Blog routes."""
from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('about', __name__)


@bp.route('/about')
@login_required
def about():
    """About Stride page - the story behind the product."""
    return render_template('about.html')


@bp.route('/blog')
@login_required
def blog():
    """Blog listing page."""
    # For now, we'll use a simple list of posts
    # Later this could be pulled from a database or CMS
    posts = [
        # {
        #     'slug': 'welcome-to-stride',
        #     'title': 'Welcome to Stride',
        #     'excerpt': 'Introducing Stride - your job search companion.',
        #     'date': '2026-02-07',
        #     'author': 'Mike Vicenzino'
        # },
    ]
    return render_template('blog.html', posts=posts)


@bp.route('/blog/<slug>')
@login_required
def blog_post(slug):
    """Individual blog post page."""
    # For now, we'll have a simple mapping of slugs to content
    # Later this could be pulled from a database or CMS
    posts = {
        # 'welcome-to-stride': {
        #     'title': 'Welcome to Stride',
        #     'date': '2026-02-07',
        #     'author': 'Mike Vicenzino',
        #     'content': '...'
        # }
    }
    
    post = posts.get(slug)
    if not post:
        return render_template('blog_post.html', post=None), 404
    
    return render_template('blog_post.html', post=post)
