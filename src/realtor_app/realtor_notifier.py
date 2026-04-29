import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_realtor_email(content):
    sender_email = "bayareavaasi@gmail.com"
    receiver_email = "bayareavaasi@gmail.com"
    password = os.getenv("GMAIL_APP_PASSWORD")

    if not password:
        return "❌ Error: GMAIL_APP_PASSWORD not set in environment."

    # Create the specialized Subject Line
    date_str = datetime.now().strftime('%d %b %Y')
    subject = f"🏠 Real Estate Scout Report — {date_str}"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    # Attach the content
    msg.attach(MIMEText(content, 'plain'))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        return "✅ Realtor Report Sent Successfully"
    except Exception as e:
        return f"💥 SMTP Error: {e}"
