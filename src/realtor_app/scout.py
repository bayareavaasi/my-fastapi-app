import os
import pandas as pd
from homeharvest import scrape_property
from datetime import datetime
import sys

# Local import for email delivery
try:
    from realtor_notifier import send_realtor_email
except ImportError:
    def send_realtor_email(content): 
        return "⚠️ Fallback: realtor_notifier.py not found."

# ---------------------------------------------------------------------------
# HOA detection — three-layer signal approach
# ---------------------------------------------------------------------------

# Layer 2: keywords scanned against the listing description text
HOA_KEYWORDS = [
    'hoa', 'homeowner', 'homeowners association',
    'community pool', 'association pool', 'clubhouse',
    'fitness center', 'community amenities',
    'association fee', 'monthly fee', 'condo fee', 'condominium fee',
]

# Layer 3: subdivision name patterns in the street field
HOA_SUBDIVISION_PATTERNS = [
    'at ', ' lake ', 'village', 'reserve', 'commons',
    'estates', 'landing', 'crossing', 'xing', 'plantation',
    'wood', 'brook', 'meadow', 'manor', 'ridge', 'haven', 'bluff', 'pointe',
]

def has_hoa_signals(row) -> bool:
    """Safely checks for HOA signals across three layers."""
    try:
        # Layer 1: explicit hoa_fee > 0
        hoa_fee = row.get('hoa_fee')
        if pd.notna(hoa_fee) and hoa_fee > 0:
            return True

        # Layer 2: keyword scan on full listing description
        desc = row.get('description') if pd.notna(row.get('description')) else row.get('text')
        text = '' if pd.isna(desc) else str(desc).lower()
        if any(kw in text for kw in HOA_KEYWORDS):
            return True

        # Layer 3: subdivision name patterns in street field
        street = '' if pd.isna(row.get('street')) else str(row.get('street', '')).lower()
        if any(p in street for p in HOA_SUBDIVISION_PATTERNS):
            return True

        return False
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Underwriting & Formatting
# ---------------------------------------------------------------------------

def estimate_monthly_cash_flow(price, est_rent):
    if not price or price < 50000: return 0 
    
    property_tax_rate = 0.012 
    insurance_monthly = 125
    maintenance_reserves = est_rent * 0.10
    vacancy_reserves = est_rent * 0.05
    
    loan_amount = price * 0.75
    r = 0.07 / 12
    n = 360
    monthly_mortgage = (loan_amount * (r * (1 + r)**n)) / ((1 + r)**n - 1)
    monthly_taxes = (price * property_tax_rate) / 12
    
    total_expenses = (monthly_mortgage + monthly_taxes + insurance_monthly + 
                      maintenance_reserves + vacancy_reserves)
    return est_rent - total_expenses

def format_realtor_report(df):
    current_date = datetime.now().strftime('%d %b %Y')
    report = f"🏠 **Saturday Real Estate Scout: Diversified Suburban Sweep**\n"
    report += f"Generated: {current_date}\n"
    report += "Criteria: Top 2 per Zip, Signal-Filtered No-HOA, No Pool, Pre-2023\n"
    report += "-------------------------------------------\n\n"

    df_sorted = df.sort_values(['zip_code', 'net_cash_flow'], ascending=[True, False])

    for _, row in df_sorted.iterrows():
        yield_pct = (row['est_monthly_rent'] / row['list_price']) * 100
        report += (
            f"📍 **{row.get('street', 'N/A')}, {row.get('city', 'N/A')} {row.get('zip_code', '')}**\n"
            f"🏙️ Submarket: {row.get('submarket', 'N/A')}\n"
            f"🏗️ Built: {int(row['year_built']) if 'year_built' in row and pd.notna(row['year_built']) else 'N/A'}\n"
            f"💰 Price: ${row['list_price']:,.0f}\n"
            f"💵 **Est. Net Cash Flow: ${row['net_cash_flow']:,.2f}/mo**\n"
            f"📈 Est. Rent: ${row['est_monthly_rent']:,.0f}/mo\n"
            f"📊 Yield Score: {yield_pct:.2f}%\n"
            f"🔗 [View Listing]({row.get('property_url', '#')})\n"
            f"-------------------------------------------\n"
        )
    return report

# ---------------------------------------------------------------------------
# Main Execution Logic
# ---------------------------------------------------------------------------

def run_scout():
    markets = [
        {"zip": "46112", "sub": "Brownsburg", "rent_factor": 0.008, "min": 1400, "max": 2800},
        {"zip": "46123", "sub": "Avon", "rent_factor": 0.008, "min": 1400, "max": 2800},
        {"zip": "46168", "sub": "Plainfield", "rent_factor": 0.0085, "min": 1300, "max": 2600},
        {"zip": "46239", "sub": "Franklin Township", "rent_factor": 0.0085, "min": 1400, "max": 2700},
        {"zip": "46143", "sub": "Greenwood", "rent_factor": 0.0085, "min": 1300, "max": 2600},
        {"zip": "46038", "sub": "Fishers", "rent_factor": 0.0075, "min": 1800, "max": 3500},
        {"zip": "64068", "sub": "Liberty", "rent_factor": 0.009, "min": 1400, "max": 2800},
        {"zip": "64118", "sub": "Gladstone", "rent_factor": 0.010, "min": 1200, "max": 2400},
        {"zip": "64152", "sub": "Parkville", "rent_factor": 0.008, "min": 1800, "max": 3800},
        {"zip": "64014", "sub": "Blue Springs", "rent_factor": 0.009, "min": 1300, "max": 2700},
        {"zip": "64081", "sub": "Lee's Summit", "rent_factor": 0.008, "min": 1600, "max": 3200},
        {"zip": "73099", "sub": "Yukon", "rent_factor": 0.010, "min": 1200, "max": 2400},
        {"zip": "73170", "sub": "South OKC/Moore", "rent_factor": 0.010, "min": 1200, "max": 2500},
        {"zip": "73034", "sub": "Edmond", "rent_factor": 0.008, "min": 1600, "max": 3500},
        {"zip": "73064", "sub": "Mustang", "rent_factor": 0.0095, "min": 1300, "max": 2600},
        {"zip": "45069", "sub": "West Chester", "rent_factor": 0.008, "min": 1800, "max": 3800},
        {"zip": "45011", "sub": "Fairfield", "rent_factor": 0.009, "min": 1500, "max": 3000},
        {"zip": "43081", "sub": "Westerville", "rent_factor": 0.0075, "min": 1800, "max": 4000},
        {"zip": "43123", "sub": "Grove City", "rent_factor": 0.0085, "min": 1500, "max": 3200},
        {"zip": "40245", "sub": "East Louisville", "rent_factor": 0.008, "min": 1700, "max": 4000}
    ]
    
    all_leads = []

    for market in markets:
        try:
            props = scrape_property(
                location=market['zip'], 
                listing_type="for_sale", 
                property_type=['SINGLE_FAMILY'], 
                past_days=7
            )
            if props.empty: continue

            # Apply Logic
            df = props[~props.apply(has_hoa_signals, axis=1)].copy()
            if df.empty: continue

            df = df[df['list_price'] > 50000]
            if 'year_built' in df.columns:
                df = df[df['year_built'] < 2023]

            # Pool filter
            pool_keywords = ['pool', 'swimming', 'in-ground', 'inground', 'above ground']
            df = df[~df.apply(lambda r: any(w in f"{str(r.get('style',''))} {str(r.get('description',''))}".lower() for w in pool_keywords), axis=1)]

            if not df.empty:
                df['submarket'] = market['sub']
                df['est_monthly_rent'] = (df['list_price'] * market['rent_factor']).clip(market['min'], market['max'])
                df['net_cash_flow'] = df.apply(lambda r: estimate_monthly_cash_flow(r['list_price'], r['est_monthly_rent']), axis=1)
                all_leads.append(df.sort_values(by='net_cash_flow', ascending=False).head(2))
                
        except Exception as e:
            print(f"⚠️ Skipping {market['zip']}: {e}")

    if not all_leads:
        return "No deals found meeting criteria."

    return format_realtor_report(pd.concat(all_leads))

if __name__ == "__main__":
    try:
        content = run_scout()
        print(content)
        send_realtor_email(content)
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        sys.exit(1)
