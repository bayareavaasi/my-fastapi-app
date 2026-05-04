import os
import pandas as pd
from homeharvest import scrape_property
from datetime import datetime

# Local import from the same directory
try:
    from realtor_notifier import send_realtor_email
except ImportError:
    def send_realtor_email(content): 
        return "⚠️ Fallback: realtor_notifier.py not found."

def estimate_monthly_cash_flow(price, est_rent):
    """
    SRE Underwriting: 25% Down, 7% Interest.
    Includes property tax, insurance, and 15% combined reserves.
    """
    if not price or price < 50000: return 0 # Guard against auctions/data errors
    
    property_tax_rate = 0.012 
    insurance_monthly = 125
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
    current_date = datetime.now().strftime('%d %b %Y')
    report = f"🏠 **Saturday Real Estate Scout: Weekly Suburban Sweep**\n"
    report += f"Generated: {current_date}\n"
    report += "Criteria: Zip-Targeted, Established (Pre-2023), No HOA, No Pool, Price > $50k\n"
    report += "-------------------------------------------\n\n"

    for _, row in df.iterrows():
        yield_pct = (row['est_monthly_rent'] / row['list_price']) * 100
        report += (
            f"📍 **{row['street']}, {row['city']} {row['zip_code']}**\n"
            f"🏙️ Submarket: {row['submarket']}\n"
            f"🏗️ Built: {int(row['year_built']) if not pd.isna(row['year_built']) else 'N/A'}\n"
            f"💰 Price: ${row['list_price']:,.0f}\n"
            f"💵 **Est. Net Cash Flow: ${row['net_cash_flow']:,.2f}/mo**\n"
            f"📈 Est. Rent: ${row['est_monthly_rent']:,.0f}/mo\n"
            f"📊 Yield Score: {yield_pct:.2f}%\n"
            f"🔗 [View Listing]({row['property_url']})\n"
            f"-------------------------------------------\n"
        )
    return report

def run_scout():
    # Targeted Market Matrix
    markets = [
        # --- Indianapolis Metro (IN) ---
        {"zip": "46112", "sub": "Brownsburg", "rent_factor": 0.008, "min": 1400, "max": 2800},
        {"zip": "46123", "sub": "Avon", "rent_factor": 0.008, "min": 1400, "max": 2800},
        {"zip": "46168", "sub": "Plainfield", "rent_factor": 0.0085, "min": 1300, "max": 2600},
        {"zip": "46239", "sub": "Franklin Township", "rent_factor": 0.0085, "min": 1400, "max": 2700},
        {"zip": "46143", "sub": "Greenwood", "rent_factor": 0.0085, "min": 1300, "max": 2600},
        {"zip": "46038", "sub": "Fishers", "rent_factor": 0.0075, "min": 1800, "max": 3500},

        # --- Kansas City Metro (MO) ---
        {"zip": "64068", "sub": "Liberty", "rent_factor": 0.009, "min": 1400, "max": 2800},
        {"zip": "64118", "sub": "Gladstone", "rent_factor": 0.010, "min": 1200, "max": 2400},
        {"zip": "64152", "sub": "Parkville", "rent_factor": 0.008, "min": 1800, "max": 3800},
        {"zip": "64014", "sub": "Blue Springs", "rent_factor": 0.009, "min": 1300, "max": 2700},
        {"zip": "64081", "sub": "Lee's Summit", "rent_factor": 0.008, "min": 1600, "max": 3200},

        # --- Oklahoma City Metro (OK) ---
        {"zip": "73099", "sub": "Yukon", "rent_factor": 0.010, "min": 1200, "max": 2400},
        {"zip": "73170", "sub": "South OKC/Moore", "rent_factor": 0.010, "min": 1200, "max": 2500},
        {"zip": "73034", "sub": "Edmond", "rent_factor": 0.008, "min": 1600, "max": 3500},
        {"zip": "73064", "sub": "Mustang", "rent_factor": 0.0095, "min": 1300, "max": 2600},

        # --- Cincinnati Metro (OH) ---
        {"zip": "45069", "sub": "West Chester", "rent_factor": 0.008, "min": 1800, "max": 3800},
        {"zip": "45011", "sub": "Fairfield", "rent_factor": 0.009, "min": 1500, "max": 3000},

        # --- Columbus Metro (OH) ---
        {"zip": "43081", "sub": "Westerville", "rent_factor": 0.0075, "min": 1800, "max": 4000},
        {"zip": "43123", "sub": "Grove City", "rent_factor": 0.0085, "min": 1500, "max": 3200},

        # --- Louisville Metro (KY) ---
        {"zip": "40245", "sub": "East Louisville", "rent_factor": 0.008, "min": 1700, "max": 4000}
    ]
    
    all_leads = []

    for market in markets:
        try:
            props = scrape_property(location=market['zip'], listing_type="for_sale", property_type=['SINGLE_FAMILY'], past_days=7)
            
            if props.empty:
                continue

            # --- FILTER LAYER 1: Standard Exclusions ---
            # 1. No HOA
            df = props[(props['hoa_fee'].isna()) | (props['hoa_fee'] == 0)].copy()
            # 2. No Auctions ($50k floor)
            df = df[df['list_price'] > 50000]

            if not df.empty:
                # --- FILTER LAYER 2: Advanced SRE Sanity Checks ---
                
                # A. Anti-Builder/New Construction (Removes hidden HOA builders)
                if 'year_built' in df.columns:
                    df = df[df['year_built'] < 2023]

                # B. Swimming Pool Exclusion
                # We check description and style fields for pool-related terms
                pool_keywords = ['pool', 'swimming', 'in-ground', 'inground', 'above ground']
                
                def check_no_pool(row):
                    # Combine all searchable text fields
                    search_text = f"{str(row.get('style', ''))} {str(row.get('description', ''))}".lower()
                    return not any(word in search_text for word in pool_keywords)

                df = df[df.apply(check_no_pool, axis=1)]

                if not df.empty:
                    df['submarket'] = market['sub']
                    df['est_monthly_rent'] = (df['list_price'] * market['rent_factor']).clip(market['min'], market['max'])
                    df['net_cash_flow'] = df.apply(lambda r: estimate_monthly_cash_flow(r['list_price'], r['est_monthly_rent']), axis=1)
                    all_leads.append(df)
                
        except Exception as e:
            print(f"Error in {market['zip']} ({market['sub']}): {e}")

    if not all_leads:
        return "No deals found meeting all SRE criteria (Established, No HOA, No Pool)."

    final_df = pd.concat(all_leads)
    top_results = final_df.sort_values(by='net_cash_flow', ascending=False).head(10)
    return format_realtor_report(top_results)

if __name__ == "__main__":
    print("🚀 Starting Hardened Suburban Scout Sweep...")
    report = run_scout()
    print(report)
    print(send_realtor_email(report))
