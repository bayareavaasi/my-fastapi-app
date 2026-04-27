import os
from pathlib import Path
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# This tells Python: "Look two folders up from this file for the .env"
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

def send_email_alert(content):
    sender_email = "bayareavaasi@gmail.com"
    receiver_email = "bayareavaasi@gmail.com" # Sending to yourself
    password = os.environ.get("GMAIL_APP_PASSWORD")

    if not password:
        return "❌ Error: GMAIL_APP_PASSWORD not set in environment" 

    # Create the email structure
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "📈 Daily Nifty IT Index Report"

    message.attach(MIMEText(content, "plain"))

    try:
        # Connect to Gmail's server (Port 587 is standard for TLS)
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls() # Secure the connection
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.quit()
        return "✅ Email sent successfully!"
    except Exception as e:
        return f"❌ Failed to send email: {e}"
