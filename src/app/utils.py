def calc_tax(price: float, tax_rate: float = 0.1, discount: float = 0.0):
	discounted_price = price * (1 - discount)
	return round(discounted_price * (1 + tax_rate), 2)
