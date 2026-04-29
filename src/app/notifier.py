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


def send_email_alert(content: str) -> str:
    sender_email = "bayareavaasi@gmail.com"
    receiver_email = "bayareavaasi@gmail.com"
    password = os.environ.get("GMAIL_APP_PASSWORD")

    if not password:
        return "❌ Error: GMAIL_APP_PASSWORD not set in environment"

    # Timestamp shows exactly when the data was fetched, regardless of
    # when GitHub Actions actually ran the job vs the scheduled cron time.
    ts = datetime.now(IST).strftime("%d %b %Y %I:%M %p IST")

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = f"📈 Daily Nifty IT Index Report — {ts}"

    message.attach(MIMEText(content, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.quit()
        return "✅ Email sent successfully!"
    except Exception as e:
        return f"❌ Failed to send email: {e}"
