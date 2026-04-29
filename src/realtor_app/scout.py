import sys
import os
import pandas as pd
from homeharvest import scrape_property  # Correct: No underscore
from datetime import datetime

# Path Hack: Add repo root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from notifier import send_email_alert
except ImportError:
    def send_email_alert(content): return "Mock Success"

def estimate_monthly_cash_flow(price, est_rent):
    if not price or not est_rent: return 0
    
    property_tax_rate = 0.012 
    insurance_monthly = 100
    maintenance_reserves = est_rent * 0.10
    vacancy_reserves = est_rent * 0.05
    
    loan_amount = price * 0.75
    r = 0.07 / 12
    n = 360
    monthly_mortgage = (loan_amount * (r * (1 + r)**n)) / ((1 + r)**n - 1)
    
    monthly_taxes = (price * property_tax_rate) / 12
    total_expenses = monthly_mortgage + monthly_taxes + insurance_monthly + maintenance_reserves + vacancy_reserves
    
    return est_rent - total_expenses

def format_realtor_report(df):
    # FIXED: Clean call, no URL artifacts
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    report = f"🏠 **Saturday Real Estate Scout: Top 5 Cash-Flow Leads**\n"
    report += f"Generated: {current_date}\n"
    report += "Criteria: Single-Family, No HOA, Sanity-Capped Rents\n"
    report += "-------------------------------------------\n\n"

    for _, row in df.iterrows():
        yield_pct = (row['est_monthly_rent'] / row['list_price']) * 100
        
        report += (
            f"📍 **{row['street']}, {row['city']}**\n"
            f"💰 Price: ${row['list_price']:,.0f}\n"
            f"💵 **Est. Net Cash Flow: ${row['net_cash_flow']:,.2f}/mo**\n"
            f"📈 Est. Rent: ${row['est_monthly_rent']:,.0f}/mo (Capped)\n"
            f"📊 Yield Score: {yield_pct:.2f}%\n"
            f"🔗 [View Listing]({row['property_url']})\n"
            f"-------------------------------------------\n"
        )
    return report

def run_scout():
    markets = [
        {
            "city": "Indianapolis", "state": "IN", 
            "rent_factor": 0.009, "rent_min": 900, "rent_max": 2200
        },
        {
            "city": "Charlotte", "state": "NC", 
            "rent_factor": 0.008, "rent_min": 1400, "rent_max": 3000
        } 
    ]
    
    all_market_leads = []

    for market in markets:
        location_str = f"{market['city']}, {market['state']}"
        try:
            properties = scrape_property(
                location=location_str,
                listing_type="for_sale",
                property_type=['SINGLE_FAMILY'],
                past_days=7
            )

            if properties.empty: continue

            no_hoa = properties[
                (properties['hoa_fee'].isna()) | (properties['hoa_fee'] == 0)
            ].copy()

            if not no_hoa.empty:
                no_hoa['est_monthly_rent'] = (
                    no_hoa['list_price'] * market['rent_factor']
                ).clip(market['rent_min'], market['rent_max'])
                
                no_hoa['net_cash_flow'] = no_hoa.apply(
                    lambda r: estimate_monthly_cash_flow(r['list_price'], r['est_monthly_rent']), 
                    axis=1
                )
                all_market_leads.append(no_hoa)

        except Exception as e:
            print(f"Error scouting {market['city']}: {e}")

    if not all_market_leads:
        return "No deals found this week."

    final_df = pd.concat(all_market_leads)
    top_5 = final_df.sort_values(by='net_cash_flow', ascending=False).head(5)
    
    return format_realtor_report(top_5)

if __name__ == "__main__":
    content = run_scout()
    print(content)
    send_email_alert(content)
