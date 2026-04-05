from fastapi import FastAPI
from pydantic import BaseModel
from .utils import calc_tax

app = FastAPI()

class Item(BaseModel):
	name: str
	price: float
	is_offer: bool = None

@app.get("/")
def read_root():
#	return {"Hello": "World"}
	return {"status": "online", "version": "1.0.0"} 

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
	return {"item_id": item_id, "q": q}

@app.post("/items/total")
def get_total(item: Item):
	discount_amount = 0.2 if item.is_offer else 0.0

	total_price = calc_tax(item.price, discount=discount_amount)
	return {
		"item_name": item.name,
		"original_price": item.price,
		"is_offer": item.is_offer,
		"total_with_tax": total_price,
		"note": "20% discount applied!" if item.is_offer else "No discount applied."
		}
