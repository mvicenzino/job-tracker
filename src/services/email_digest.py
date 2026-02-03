"""Email digest service for sending follow-up reminders."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
from typing import List, Dict, Any


def is_email_configured() -> bool:
    """Check if SMTP email is configured."""
    return bool(os.environ.get('SMTP_HOST') and os.environ.get('SMTP_USER'))


def send_email(to_email: str, subject: str, html_body: str, text_body: str = None) -> bool:
    """Send an email using SMTP configuration from environment."""
    if not is_email_configured():
        return False

    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    from_email = os.environ.get('SMTP_FROM', smtp_user)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"Stride <{from_email}>"
    msg['To'] = to_email

    if text_body:
        msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def generate_digest_email(digest_data: Dict[str, Any], user_email: str) -> tuple:
    """Generate HTML and text versions of the digest email."""
    today = date.today().strftime('%B %d, %Y')

    followups = digest_data.get('followups_needed', [])
    stale_leads = digest_data.get('stale_leads', [])
    stale_apps = digest_data.get('stale_applications', [])
    today_events = digest_data.get('today_events', [])

    # Count items needing attention
    total_action_items = len(followups) + len(stale_leads) + len(stale_apps)

    # Generate HTML email
    html_parts = [f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #6366f1; font-size: 24px; margin-bottom: 8px; }}
        h2 {{ color: #374151; font-size: 18px; margin: 24px 0 12px; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px; }}
        .summary {{ background: #f3f4f6; padding: 16px; border-radius: 8px; margin-bottom: 24px; }}
        .summary strong {{ color: #6366f1; font-size: 32px; }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 8px 0; }}
        .company {{ color: #6b7280; font-size: 14px; }}
        .overdue {{ color: #ef4444; font-weight: 500; }}
        .cta {{ display: inline-block; background: #6366f1; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; margin-top: 16px; }}
        .footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #9ca3af; }}
    </style>
</head>
<body>
    <h1>Your Stride Digest</h1>
    <p style="color: #6b7280; margin-top: 0;">{today}</p>

    <div class="summary">
        <strong>{total_action_items}</strong> items need your attention
    </div>
''']

    # Follow-ups section
    if followups:
        html_parts.append('<h2>Follow-ups Due</h2><ul>')
        for contact in followups[:10]:
            company = f' <span class="company">at {contact.company.name}</span>' if contact.company else ''
            overdue = ' <span class="overdue">(overdue)</span>' if contact.next_followup_date < date.today() else ''
            html_parts.append(f'<li><strong>{contact.name}</strong>{company}{overdue}</li>')
        if len(followups) > 10:
            html_parts.append(f'<li>...and {len(followups) - 10} more</li>')
        html_parts.append('</ul>')

    # Today's events
    if today_events:
        html_parts.append('<h2>Today\'s Events</h2><ul>')
        for event in today_events:
            time_str = event.start_time.strftime('%-I:%M %p')
            html_parts.append(f'<li><strong>{time_str}</strong> - {event.title}</li>')
        html_parts.append('</ul>')

    # Stale leads
    if stale_leads:
        html_parts.append('<h2>Stale Leads (14+ days)</h2><ul>')
        for app in stale_leads[:5]:
            html_parts.append(f'<li>{app.job.title} <span class="company">at {app.job.company.name}</span></li>')
        if len(stale_leads) > 5:
            html_parts.append(f'<li>...and {len(stale_leads) - 5} more</li>')
        html_parts.append('</ul>')

    # Stale applications
    if stale_apps:
        html_parts.append('<h2>Awaiting Response (14+ days)</h2><ul>')
        for app in stale_apps[:5]:
            html_parts.append(f'<li>{app.job.title} <span class="company">at {app.job.company.name}</span></li>')
        if len(stale_apps) > 5:
            html_parts.append(f'<li>...and {len(stale_apps) - 5} more</li>')
        html_parts.append('</ul>')

    # No action items
    if total_action_items == 0 and not today_events:
        html_parts.append('<p>Nothing needs your attention today. Keep up the great work!</p>')

    html_parts.append('''
    <a href="#" class="cta">Open Stride</a>

    <div class="footer">
        <p>You're receiving this because you enabled email digests in Stride settings.</p>
        <p>To unsubscribe, visit your <a href="#">notification settings</a>.</p>
    </div>
</body>
</html>
''')

    html_body = ''.join(html_parts)

    # Generate plain text version
    text_parts = [f"Your Stride Digest - {today}\n", "=" * 40, "\n\n"]
    text_parts.append(f"{total_action_items} items need your attention\n\n")

    if followups:
        text_parts.append("FOLLOW-UPS DUE\n")
        text_parts.append("-" * 20 + "\n")
        for contact in followups[:10]:
            company = f" at {contact.company.name}" if contact.company else ""
            text_parts.append(f"- {contact.name}{company}\n")
        text_parts.append("\n")

    if today_events:
        text_parts.append("TODAY'S EVENTS\n")
        text_parts.append("-" * 20 + "\n")
        for event in today_events:
            time_str = event.start_time.strftime('%-I:%M %p')
            text_parts.append(f"- {time_str}: {event.title}\n")
        text_parts.append("\n")

    if stale_leads:
        text_parts.append("STALE LEADS\n")
        text_parts.append("-" * 20 + "\n")
        for app in stale_leads[:5]:
            text_parts.append(f"- {app.job.title} at {app.job.company.name}\n")
        text_parts.append("\n")

    text_body = ''.join(text_parts)

    return html_body, text_body


def send_digest_to_user(user, service) -> bool:
    """Send digest email to a user."""
    if not user.email_digest_enabled:
        return False

    if not is_email_configured():
        return False

    digest = service.get_daily_digest()

    # Skip if nothing to report
    if not digest.get('has_action_items') and not digest.get('today_events'):
        return False

    html_body, text_body = generate_digest_email(digest, user.email)
    subject = f"Stride Digest: {len(digest.get('followups_needed', []))} follow-ups due"

    return send_email(user.email, subject, html_body, text_body)
