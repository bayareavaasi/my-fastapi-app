import sys
import os
import pandas as pd
from homeharvest import scrape_property
from datetime import datetime

# Path hack: add src/ to sys.path so notifier can be found in CI
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

try:
    from notifier import send_email_alert
except ImportError:
    def send_email_alert(content, subject=None): return "Mock: email not sent"

# ---------------------------------------------------------------------------
# HOA detection — three-layer signal approach
# ---------------------------------------------------------------------------

# Layer 2: keywords scanned against the listing description text
HOA_KEYWORDS = [
    'hoa',
    'homeowner',
    'homeowners association',
    'community pool',
    'association pool',
    'clubhouse',
    'fitness center',
    'community amenities',
    'association fee',
    'monthly fee',
    'condo fee',
    'condominium fee',
]

# Layer 3: subdivision name patterns in the street field
# Expanded after filter testing against 40 real listings (7 misses identified)
HOA_SUBDIVISION_PATTERNS = [
    'at ',           # e.g. "Troon at Landis Lake"
    ' lake ',        # spaced to avoid partial matches like "Lakewood Ave"
    'village',
    'reserve',
    'commons',
    'estates',
    'landing',
    'crossing',
    'xing',          # abbreviation for crossing (e.g. "Ross Xing")
    'plantation',
    'wood',          # e.g. "Summerwood", "Wildwood"
    'brook',         # e.g. "Shadowbrook"
    'meadow',
    'manor',
    'ridge',
    'haven',
    'bluff',
    'pointe',
]


def has_hoa_signals(row) -> bool:
    """
    Returns True if any of three HOA signal layers are detected.

    Layer 1 — explicit hoa_fee > 0
    Layer 2 — keyword scan on listing description text
    Layer 3 — subdivision name patterns in street address
    """
    # Layer 1: explicit fee published
    hoa_fee = row.get('hoa_fee')
    if pd.notna(hoa_fee) and hoa_fee > 0:
        return True

    # Layer 2: keyword scan on full listing description
    text = '' if pd.isna(row.get('text')) else str(row.get('text', '')).lower()
    if any(kw in text for kw in HOA_KEYWORDS):
        return True

    # Layer 3: subdivision name patterns in street field
    street = '' if pd.isna(row.get('street')) else str(row.get('street', '')).lower()
    if any(p in street for p in HOA_SUBDIVISION_PATTERNS):
        return True

    return False


# ---------------------------------------------------------------------------
# Cash flow calculator
# ---------------------------------------------------------------------------

def estimate_monthly_cash_flow(price: float, est_rent: float) -> float:
    """
    Returns estimated monthly net cash flow after all standard SFH expenses.

    Assumptions:
    - 25% down, 7% interest, 30-year fixed mortgage
    - 1.2% annual property tax (non-owner-occupied IN rate)
    - $100/mo insurance
    - 10% maintenance reserve on rent
    - 5% vacancy reserve on rent
    """
    if not price or not est_rent:
        return 0.0

    property_tax_rate = 0.012
    insurance_monthly = 100
    maintenance_reserves = est_rent * 0.10
    vacancy_reserves = est_rent * 0.05

    loan_amount = price * 0.75
    r = 0.07 / 12
    n = 360
    monthly_mortgage = (loan_amount * (r * (1 + r) ** n)) / ((1 + r) ** n - 1)

    monthly_taxes = (price * property_tax_rate) / 12
    total_expenses = (
        monthly_mortgage
        + monthly_taxes
        + insurance_monthly
        + maintenance_reserves
        + vacancy_reserves
    )

    return est_rent - total_expenses


# ---------------------------------------------------------------------------
# Report formatter
# ---------------------------------------------------------------------------

def format_realtor_report(df: pd.DataFrame) -> str:
    current_date = datetime.now().strftime('%Y-%m-%d')
    report = "🏠 **Saturday Real Estate Scout: Top 5 Cash-Flow Leads**\n"
    report += f"Generated: {current_date}\n"
    report += "Criteria: Single-Family, No HOA (3-layer filter), Sanity-Capped Rents\n"
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


# ---------------------------------------------------------------------------
# Main scout
# ---------------------------------------------------------------------------

def run_scout() -> str:
    # SRE target markets with rent factor and sanity bands
    markets = [
        {
            "city": "Indianapolis", "state": "IN",
            "rent_factor": 0.009, "rent_min": 900, "rent_max": 2200,
        },
        {
            "city": "Charlotte", "state": "NC",
            "rent_factor": 0.008, "rent_min": 1400, "rent_max": 3000,
        },
    ]

    all_market_leads = []

    for market in markets:
        location_str = f"{market['city']}, {market['state']}"
        print(f"🔍 Scouting {location_str}...")

        try:
            properties = scrape_property(
                location=location_str,
                listing_type="for_sale",
                property_type=['SINGLE_FAMILY'],
                past_days=7,
            )
        except Exception as e:
            print(f"Error scouting {market['city']}: {e}")
            continue

        if properties.empty:
            print(f"No new listings found in {market['city']}.")
            continue

        # Apply 3-layer HOA filter
        no_hoa = properties[~properties.apply(has_hoa_signals, axis=1)].copy()

        if no_hoa.empty:
            print(f"No HOA-free listings found in {market['city']}.")
            continue

        # Estimate rent with sanity clipping
        no_hoa['est_monthly_rent'] = (
            no_hoa['list_price'] * market['rent_factor']
        ).clip(market['rent_min'], market['rent_max'])

        # Calculate net cash flow
        no_hoa['net_cash_flow'] = no_hoa.apply(
            lambda r: estimate_monthly_cash_flow(
                r['list_price'], r['est_monthly_rent']
            ),
            axis=1,
        )

        all_market_leads.append(no_hoa)

    if not all_market_leads:
        return "No deals found this week."

    final_df = pd.concat(all_market_leads)
    top_5 = final_df.sort_values(by='net_cash_flow', ascending=False).head(5)

    return format_realtor_report(top_5)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    content = run_scout()
    print(content)
    print("Attempting to send email...")
    ts = datetime.now().strftime("%d %b %Y %I:%M %p")
    result = send_email_alert(
        content,
        subject=f"🏠 Saturday Real Estate Scout — {ts}"
    )
    print(result)
