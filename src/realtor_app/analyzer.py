def estimate_monthly_cash_flow(price, est_rent):
    """
    Calculates estimated monthly net cash flow.
    """
    # Assumptions for a $200k-$300k SFH in Indy
    property_tax_rate = 0.012  # ~1.2% for non-owner occupied in IN
    insurance_monthly = 100
    maintenance_reserves = est_rent * 0.10
    vacancy_reserves = est_rent * 0.05
    
    # 25% Down, 7% Interest (Standard Investment Loan)
    down_payment = price * 0.25
    loan_amount = price * 0.75
    # Monthly P&I (Principal and Interest)
    monthly_mortgage = (loan_amount * (0.07 / 12) * (1 + 0.07 / 12)**360) / ((1 + 0.07 / 12)**360 - 1)
    
    monthly_taxes = (price * property_tax_rate) / 12
    
    total_expenses = monthly_mortgage + monthly_taxes + insurance_monthly + maintenance_reserves + vacancy_reserves
    
    return est_rent - total_expenses

def calculate_yield(price, est_rent):
    # The Gross Rent Multiplier (GRM) or 1% Rule check
    if price == 0: return 0
    return (est_rent / price) * 100
