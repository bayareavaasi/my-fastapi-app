"""
Weekly real-estate scout.

Scrapes for-sale single-family listings (past 7 days) across the top-10
investment ZIPs via homeharvest, filters out likely-HOA properties, pools
and new construction, underwrites each with market-specific investor tax
rates, keeps listings with cash flow >= -$500/mo, and emails an
appreciation-ranked report.

Market list researched Oct 2026 against: 3-5yr appreciation (primary),
landlord insurance cost, investor property tax, hurricane/flood/wildfire
risk, job growth, schools, hospital access, cash-flow viability.
Full research: ~/workspace/research_notes/top-10-investment-zip-codes-*/

Run from the project root:
    python src/realtor_app/scout.py
or as a module from src/:
    python -m realtor_app.scout

Requires GMAIL_APP_PASSWORD in the environment (see .env.example).
"""

import sys
from datetime import datetime

import pandas as pd
from homeharvest import scrape_property

# --- local imports (work both as a package and as loose scripts) ---
try:
    # running as a module: python -m realtor_app.scout (from src/)
    from realtor_app.analyzer import estimate_monthly_cash_flow
except ImportError:
    # running the file directly: python src/realtor_app/scout.py
    from analyzer import estimate_monthly_cash_flow

try:
    from realtor_app.realtor_notifier import send_realtor_email
except ImportError:
    try:
        from realtor_notifier import send_realtor_email
    except ImportError:
        def send_realtor_email(content):
            return "⚠️ Fallback: realtor_notifier.py not found; email not sent."


# Cash-flow floor: small monthly losses are acceptable because
# appreciation (3-5yr outlook) is the primary criterion.
CASH_FLOW_FLOOR = -500


# ---------------------------------------------------------------------------
# HOA detection — three-layer signal approach (no-HOA-fee requirement holds)
# ---------------------------------------------------------------------------

# Layer 2: keywords scanned against the listing description text
HOA_KEYWORDS = [
    'hoa', 'homeowner', 'homeowners association',
    'community pool', 'association pool', 'clubhouse',
    'fitness center', 'community amenities',
    'association fee', 'monthly fee', 'condo fee', 'condominium fee',
]

# Layer 3: subdivision name patterns in the street field.
# NOTE: this layer is aggressive -- ordinary street names like "Oakwood Dr"
# or "Brook Ln" match patterns like 'wood'/'brook' and get filtered out even
# with no HOA. Consider pointing it at a subdivision/community column
# instead, or downgrading it to a warning flag rather than a hard filter.
HOA_SUBDIVISION_PATTERNS = [
    'at ', ' lake ', 'village', 'reserve', 'commons',
    'estates', 'landing', 'crossing', 'xing', 'plantation',
    'wood', 'brook', 'meadow', 'manor', 'ridge', 'haven', 'bluff', 'pointe',
]


def has_hoa_signals(row) -> bool:
    """
    Returns True if any of three HOA signal layers are detected.
    Layer 1 — explicit hoa_fee > 0
    Layer 2 — keyword scan on listing description text
    Layer 3 — subdivision name patterns in street address
    """
    try:
        # Layer 1: explicit fee published
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
# Report Formatting
# ---------------------------------------------------------------------------

def format_realtor_report(df):
    current_date = datetime.now().strftime('%d %b %Y')
    report = f"🏠 **Real Estate Scout: Top-10 Investment ZIP Sweep**\n"
    report += f"Generated: {current_date}\n"
    report += ("Criteria: Appreciation-ranked, Top 2 per Zip, Signal-Filtered No-HOA, "
               "No Pool, Pre-2023, Cash flow >= -$500/mo\n")
    report += "-------------------------------------------\n\n"

    # Sort by appreciation outlook (best first, unknown last), then cash flow
    df_sorted = df.sort_values(['appr', 'net_cash_flow'],
                               ascending=[False, False], na_position='last')

    for _, row in df_sorted.iterrows():
        yield_pct = (row['est_monthly_rent'] / row['list_price']) * 100
        appr_str = f"{row['appr']:+.1f}%" if pd.notna(row.get('appr')) else "n/a"
        report += (
            f"📍 **{row.get('street', 'N/A')}, {row.get('city', 'N/A')} {row.get('zip_code', '')}**\n"
            f"🏙️ Submarket: {row.get('submarket', 'N/A')}\n"
            f"🚀 Appreciation outlook: {appr_str} ({row.get('appr_note', '')})\n"
            f"🏗️ Built: {int(row['year_built']) if 'year_built' in row and pd.notna(row['year_built']) else 'N/A'}\n"
            f"💰 Price: ${row['list_price']:,.0f}\n"
            f"💵 **Est. Net Cash Flow: ${row['net_cash_flow']:,.2f}/mo**\n"
            f"📈 Est. Rent: ${row['est_monthly_rent']:,.0f}/mo\n"
            f"📊 Yield Score: {yield_pct:.2f}%\n"
            f"📝 Note: {row.get('market_note', 'N/A')}\n"
            f"🔗 [View Listing]({row.get('property_url', '#')})\n"
            f"-------------------------------------------\n"
        )
    return report


# ---------------------------------------------------------------------------
# Main Execution Logic
# ---------------------------------------------------------------------------

def run_scout():
    # Top-10 investment ZIPs, ranked by 3-5yr appreciation outlook (primary).
    # rent_factor/min/max: rent heuristic per ZIP (rent = price x factor, clamped).
    # tax_rate: investor-effective property tax (non-owner-occupant).
    # appr: Zillow metro appreciation forecast % (None where unpublished).
    markets = [
        {"zip": "37918", "sub": "Fountain City / N. Knoxville, TN",
         "rent_factor": 0.0065, "min": 1300, "max": 2400,
         "tax_rate": 0.0072, "appr": 3.9, "appr_note": "Zillow metro forecast",
         "note": "Cheapest landlord insurance of set; Shannondale Elem 9/10."},
        {"zip": "46229", "sub": "East Indy / Lawrence, IN",
         "rent_factor": 0.0082, "min": 1200, "max": 2200,
         "tax_rate": 0.012, "appr": 2.9, "appr_note": "Zillow metro forecast",
         "note": "Only cash-flow-positive of set; favor Lawrence Twp side for schools."},
        {"zip": "43068", "sub": "Reynoldsburg / Columbus, OH",
         "rent_factor": 0.0068, "min": 1400, "max": 2400,
         "tax_rate": 0.015, "appr": 2.7, "appr_note": "Zillow metro forecast",
         "note": "Intel/Anduril jobs; ZIP-level rent data thin — verify."},
        {"zip": "44126", "sub": "Fairview Park / Cleveland, OH",
         "rent_factor": 0.0065, "min": 1300, "max": 2200,
         "tax_rate": 0.022, "appr": 3.4, "appr_note": "Zillow metro forecast",
         "note": "Investor tax ~2.3% drags cash flow; check Rocky River flood corridor per address."},
        {"zip": "64138", "sub": "South KC / Raytown, MO",
         "rent_factor": 0.0071, "min": 1200, "max": 2000,
         "tax_rate": 0.01, "appr": 2.7, "appr_note": "Zillow metro forecast",
         "note": "Thinnest ZIP-level data of set — verify; favor Raytown C-2 side."},
        {"zip": "63129", "sub": "Oakville / Mehlville / St. Louis, MO",
         "rent_factor": 0.0062, "min": 1400, "max": 2300,
         "tax_rate": 0.01, "appr": 2.2, "appr_note": "Zillow metro forecast",
         "note": "ZIP-level rent data thin — verify."},
        {"zip": "37013", "sub": "Antioch / Nashville, TN",
         "rent_factor": 0.0057, "min": 1600, "max": 2600,
         "tax_rate": 0.007, "appr": 2.1, "appr_note": "Zillow metro forecast",
         "note": "Soft renter market (8.3% vacancy); check FEMA Mill Creek corridor per address; favor Cane Ridge pocket."},
        {"zip": "35810", "sub": "NW Huntsville, AL",
         "rent_factor": 0.0067, "min": 1100, "max": 1800,
         "tax_rate": 0.013, "appr": -1.2,
         "appr_note": "STALE Jun25-Jun26 vintage — ranked on jobs/cash flow",
         "note": "Strongest job growth of set; AL Class II investor assessment (20%); verify Madison Co. millage."},
        {"zip": "53220", "sub": "Greenfield / Milwaukee, WI",
         "rent_factor": 0.0064, "min": 1300, "max": 2200,
         "tax_rate": 0.017, "appr": 3.2, "appr_note": "Zillow metro forecast",
         "price_cap": 290000,
         "note": "Must buy at/under $290k for the cash-flow screen; ZIP-level SFH rent thin — verify."},
        {"zip": "68127", "sub": "Millard / Omaha, NE",
         "rent_factor": 0.0067, "min": 1400, "max": 2300,
         "tax_rate": 0.0163, "appr": None,
         "appr_note": "no published forecast — ranked on schools/market tightness",
         "note": "Millard schools Niche A; ZIP spans 3 districts — favor Millard side; check Papillion Creek flood per address."},
    ]

    all_leads = []

    for market in markets:
        try:
            print(f"Scouting {market['sub']} ({market['zip']})...")
            props = scrape_property(
                location=market['zip'],
                listing_type="for_sale",
                property_type=['SINGLE_FAMILY'],
                past_days=7
            )
            if props.empty:
                continue

            # --- FILTER LAYER 1: Explicit & Signal-Based HOA ---
            df = props[~props.apply(has_hoa_signals, axis=1)].copy()
            if df.empty:
                continue

            # --- FILTER LAYER 2: Price band, Auctions & New Construction ---
            df = df[df['list_price'] > 50000]
            if market.get('price_cap'):
                df = df[df['list_price'] <= market['price_cap']]
            if 'year_built' in df.columns:
                df = df[df['year_built'] < 2023]
            if df.empty:
                continue

            # --- FILTER LAYER 3: Swimming Pool ---
            pool_keywords = ['pool', 'swimming', 'in-ground', 'inground', 'above ground']
            df = df[~df.apply(
                lambda r: any(w in f"{str(r.get('style', ''))} {str(r.get('description', ''))}".lower()
                              for w in pool_keywords),
                axis=1)]

            if not df.empty:
                # Remove duplicate addresses before picking top 2
                df = df.drop_duplicates(subset=['street'])

                df['submarket'] = market['sub']
                df['appr'] = market['appr']
                df['appr_note'] = market['appr_note']
                df['market_note'] = market['note']
                df['est_monthly_rent'] = (df['list_price'] * market['rent_factor']).clip(
                    market['min'], market['max'])
                df['net_cash_flow'] = df.apply(
                    lambda r: estimate_monthly_cash_flow(
                        r['list_price'], r['est_monthly_rent'], market['tax_rate']),
                    axis=1)

                # Cash-flow screen: small monthly losses acceptable
                df = df[df['net_cash_flow'] >= CASH_FLOW_FLOOR]
                if df.empty:
                    continue

                # Zip-Level Diversification: Top 2 per Zip
                all_leads.append(df.sort_values(by='net_cash_flow', ascending=False).head(2))

        except Exception as e:
            print(f"⚠️ Market Error {market['zip']}: {e}")

    if not all_leads:
        return "No deals found meeting criteria."

    final_df = pd.concat(all_leads)
    return format_realtor_report(final_df)


if __name__ == "__main__":
    try:
        print("🚀 Starting Top-10 Investment ZIP Scout...")
        content = run_scout()
        print(content)
        print(send_realtor_email(content))
    except Exception as e:
        print(f"FATAL: {e}")
        sys.exit(1)
