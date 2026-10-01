"""
Shared underwriting math for the real-estate scout.

Canonical assumptions (tune here to change every report at once):
- Investment loan: 25% down, 30-yr fixed at 7%
- Property tax: 1.2%/yr of list price (IN non-owner-occupied ballpark)
- Landlord insurance: $125/mo
- Maintenance reserve: 10% of rent
- Vacancy reserve: 5% of rent
- Listings under $50k are treated as non-viable (auction/land/teardown)

NOTE: no property-management fee is included yet. For out-of-state
landlording that typically runs 8-10% of rent -- add it before
trusting a "positive" cash-flow number.
"""

DOWN_PAYMENT_PCT = 0.25
MORTGAGE_RATE = 0.07
MORTGAGE_TERM_MONTHS = 360
PROPERTY_TAX_RATE = 0.012  # ~1.2% for non-owner occupied in IN
INSURANCE_MONTHLY = 125
MAINTENANCE_RESERVE_PCT = 0.10
VACANCY_RESERVE_PCT = 0.05
MIN_PRICE = 50000


def estimate_monthly_cash_flow(price, est_rent, tax_rate=None):
    """
    Calculates estimated monthly net cash flow.

    price: listing price of the property
    est_rent: estimated monthly rent
    tax_rate: investor-effective annual property tax rate; defaults to
        PROPERTY_TAX_RATE (IN non-owner-occupied ballpark). Pass a
        market-specific rate for out-of-state investor math.
    """
    if not price or price < MIN_PRICE:
        return 0

    loan_amount = price * (1 - DOWN_PAYMENT_PCT)

    # Monthly P&I (Principal and Interest), standard amortization formula
    r = MORTGAGE_RATE / 12
    n = MORTGAGE_TERM_MONTHS
    monthly_mortgage = (loan_amount * (r * (1 + r) ** n)) / ((1 + r) ** n - 1)

    rate = PROPERTY_TAX_RATE if tax_rate is None else tax_rate
    monthly_taxes = (price * rate) / 12
    maintenance_reserves = est_rent * MAINTENANCE_RESERVE_PCT
    vacancy_reserves = est_rent * VACANCY_RESERVE_PCT

    total_expenses = (monthly_mortgage + monthly_taxes + INSURANCE_MONTHLY +
                      maintenance_reserves + vacancy_reserves)

    return est_rent - total_expenses


def calculate_yield(price, est_rent):
    """
    Monthly gross rent as a percentage of price.
    The classic "1% rule" target is 1.0 here.
    """
    if not price:
        return 0
    return (est_rent / price) * 100
