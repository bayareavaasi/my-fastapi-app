import yfinance as yf
from notifier import send_email_alert
from datetime import datetime, time
import pytz

TICKER_SYMBOL = "^CNXIT"
IST = pytz.timezone("Asia/Kolkata")


def is_market_closed() -> bool:
    """Returns True if the NSE market session has ended for today (after 15:30 IST)."""
    now_ist = datetime.now(IST)
    return now_ist.time() > time(15, 30)


def get_nifty_it_status() -> str:
    """
    Fetches the latest Nifty IT index data and calculates daily change.
    Uses a 5-day window to handle weekends and market holidays.

    - If the market has closed today, compares today's close vs previous close.
    - If the market is still open, reports the live price vs previous close.
    """
    try:
        it_index = yf.Ticker(TICKER_SYMBOL)
        hist = it_index.history(period="5d")
    except Exception as e:
        return f"Error fetching data from yfinance: {e}"

    if len(hist) < 2:
        return "Error: not enough historical data found to calculate change."

    if is_market_closed():
        # Session over — the last row is today's finalised close
        latest_price = hist["Close"].iloc[-1]
        prev_close = hist["Close"].iloc[-2]
        price_label = "LTP (Close)"
    else:
        # Market still open — today's row may be incomplete or absent.
        # Use the live regularMarketPrice and treat the last closed row as prev close.
        info = it_index.info
        live_price = info.get("regularMarketPrice")

        if live_price:
            latest_price = live_price
            prev_close = hist["Close"].iloc[-1]  # last fully closed session
            price_label = "Live Price"
        else:
            # Fallback if live price unavailable
            latest_price = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[-2]
            price_label = "LTP"

    change_pct = ((latest_price - prev_close) / prev_close) * 100

    return (
        f"Nifty IT Index Update\n"
        f"{price_label}: {latest_price:.2f}\n"
        f"Previous Close: {prev_close:.2f}\n"
        f"Daily Change: {change_pct:+.2f}%"
    )


if __name__ == "__main__":
    # 1. Generate the report
    report = get_nifty_it_status()
    print(report)

    # 2. Trigger the email notification
    print("Attempting to send email...")
    result = send_email_alert(report)
    print(result)
