import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import pytz
from dotenv import load_dotenv

# Look two folders up from this file for the .env (local dev only)
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

IST = pytz.timezone("Asia/Kolkata")


def _build_html(content: str) -> str:
    """
    Converts a plain-text report (with markdown-style formatting) into
    a clean HTML email body. Handles **bold**, bullet lines, and URLs.
    """
    import re
    lines = content.splitlines()
    html_lines = []

    for line in lines:
        # Section divider
        if line.strip().startswith("---"):
            html_lines.append("<hr style='border:none;border-top:1px solid #eee;margin:8px 0;'>")
            continue

        # Bold: **text**
        line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)

        # Markdown link: [text](url)
        line = re.sub(
            r'\[([^\]]+)\]\((https?://[^\)]+)\)',
            r'<a href="\2" style="color:#1a73e8;">\1</a>',
            line
        )

        if line.strip():
            html_lines.append(f"<p style='margin:4px 0;'>{line}</p>")
        else:
            html_lines.append("<br>")

    return f"""
    <div style="font-family:Arial,sans-serif;font-size:14px;color:#333;
                max-width:600px;margin:0 auto;padding:16px;">
        {''.join(html_lines)}
    </div>
    """


def send_email_alert(content: str, subject: str = None) -> str:
    """
    Sends an HTML email alert.

    Args:
        content: Plain-text report body (supports **bold** and [link](url) markdown).
        subject: Optional custom subject line. Defaults to a timestamped Nifty IT subject.
    """
    sender_email = "bayareavaasi@gmail.com"
    receiver_email = "bayareavaasi@gmail.com"
    password = os.environ.get("GMAIL_APP_PASSWORD")

    if not password:
        return "❌ Error: GMAIL_APP_PASSWORD not set in environment"

    # Default subject with IST timestamp (used by Nifty IT monitor)
    if subject is None:
        ts = datetime.now(IST).strftime("%d %b %Y %I:%M %p IST")
        subject = f"📈 Daily Nifty IT Index Report — {ts}"

    message = MIMEMultipart("alternative")
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    # Attach both plain text (fallback) and HTML parts
    message.attach(MIMEText(content, "plain"))
    message.attach(MIMEText(_build_html(content), "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.quit()
        return "✅ Email sent successfully!"
    except Exception as e:
        return f"❌ Failed to send email: {e}"
