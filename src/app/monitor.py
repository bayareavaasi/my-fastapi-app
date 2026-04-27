import yfinance as yf

def get_nifty_it_status():
    # NSE Ticker for Nifty IT is ^CNXIT
    ticker = "^CNXIT"
    
    # Fetch 5 days of data to ensure we have enough for a day-over-day comparison
    it_index = yf.Ticker(ticker)
    df = it_index.history(period="5d")
    
    if df.empty or len(df) < 2:
        return "⚠️ Error: Could not fetch market data."

    # Get the last two closing prices
    # .iloc[-1] is today/most recent, .iloc[-2] is the previous session
    latest_close = df['Close'].iloc[-1]
    prev_close = df['Close'].iloc[-2]
    
    # Calculate percentage change
    change_pct = ((latest_close - prev_close) / prev_close) * 100
    
    # Return a formatted string
    status = (
        f"🖥️ **Nifty IT Index Update**\n"
        f"Last Close: {latest_close:.2f}\n"
        f"Daily Change: {change_pct:+.2f}%"
    )
    
    return status

if __name__ == "__main__":
    print(get_nifty_it_status())
