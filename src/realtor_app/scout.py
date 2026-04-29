import os
import pandas as pd
from homeharvest import scrape_property
from datetime import datetime

# Local import from the same directory (src/realtor_app)
try:
    from realtor_notifier import send_realtor_email
except ImportError:
    # Fixed fallback name to prevent NameError in __main__
    def send_realtor_email(content): 
        return "⚠️ Fallback: realtor_notifier.py not found in local path."

def estimate_monthly_cash_flow(price, est_rent):
    """
    Deterministic cash flow calculation for a 25% down, 30yr fixed mortgage at 7%.
    Includes reserves for taxes, insurance, maintenance, and vacancy.
    """
    if not price or not est_rent:
        return 0
    
    # Assumptions
    property_tax_rate = 0.012  # 1.2% annual
    insurance_monthly = 100
    maintenance_reserves = est_rent * 0.10
    vacancy_reserves = est_rent * 0.05
    
    # Financing
    loan_amount = price * 0.75
    r = 0.07 / 12  # Monthly interest rate
    n = 360        # 30 years
    
    # Standard Amortization Formula
    monthly_mortgage = (loan_amount * (r * (1 + r)**n)) / ((1 + r)**n - 1)
    monthly_taxes = (price * property_tax_rate) / 12
    
    total_expenses = monthly_mortgage + monthly_taxes + insurance_monthly + maintenance_reserves + vacancy_reserves
    return est_rent - total_expenses

def format_realtor_report(df):
    """
    Generates a clean Markdown-ready report for the email body.
    """
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    report = f"🏠 **Saturday Real Estate Scout: Top 10 Cash-Flow Leads**\n"
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
    """
    Scrapes selected markets, applies investor filters, and ranks by cash flow.
    """
    markets = [
        {
            "city": "Indianapolis", "state": "IN", 
            "rent_factor": 0.009, "rent_min": 900, "rent_max": 2200
        },
        {
            "city": "Charlotte", "state": "NC", 
            "rent_factor": 0.008, "rent_min": 1400, "rent_max": 3000
        },
        {
            "city": "Kansas City", "state": "MO", 
            "rent_factor": 0.010, "rent_min": 1000, "rent_max": 2500
        },
        {
            "city": "Oklahoma City", "state": "OK", 
            "rent_factor": 0.011, "rent_min": 900, "rent_max": 2100
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

            if properties.empty:
                continue

            # Filter for No HOA or Zero HOA fees
            no_hoa = properties[
                (properties['hoa_fee'].isna()) | (properties['hoa_fee'] == 0)
            ].copy()

            if not no_hoa.empty:
                # 1. Apply Rent Factor and Sanity Bands
                no_hoa['est_monthly_rent'] = (
                    no_hoa['list_price'] * market['rent_factor']
                ).clip(market['rent_min'], market['rent_max'])
                
                # 2. Calculate Net Monthly Cash Flow
                no_hoa['net_cash_flow'] = no_hoa.apply(
                    lambda r: estimate_monthly_cash_flow(r['list_price'], r['est_monthly_rent']), 
                    axis=1
                )
                all_market_leads.append(no_hoa)

        except Exception as e:
            print(f"Error scouting {market['city']}: {e}")

    if not all_market_leads:
        return "No deals found this week that meet the 'No HOA' criteria."

    # Concatenate results and rank by the best dollar-for-dollar cash flow
    final_df = pd.concat(all_market_leads)
    top_10 = final_df.sort_values(by='net_cash_flow', ascending=False).head(10)
    
    return format_realtor_report(top_10)

if __name__ == "__main__":
    print("🚀 Starting Real Estate Scout...")
    report_content = run_scout()
    
    print(report_content)
    
    print("Attempting to send email via realtor_notifier...")
    status = send_realtor_email(report_content)
    print(f"Final Status: {status}")
