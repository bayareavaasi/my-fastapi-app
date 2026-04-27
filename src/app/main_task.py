from monitor import get_nifty_it_status
from notifier import send_email_alert

def run_daily_job():
    status_report = get_nifty_it_status()
    result = send_email_alert(status_report)
    print(result)

if __name__ == "__main__":
    run_daily_job()
