import os
import time
import logging
import threading
from fastapi import FastAPI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()
APP_ENV = os.getenv("APP_ENV", "production")
APP_VERSION = os.getenv("APP_VERSION", "1.2.0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler("production.log"), logging.StreamHandler()]
)
logger = logging.getLogger("InventoryProductionService")

app = FastAPI(title="Inventory Management Production API", version=APP_VERSION)
START_TIME = time.time()

class ItemCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    quantity: int = Field(..., ge=0)
    price: float = Field(..., ge=0.0)

class ProductionInventoryStore:
    def __init__(self):
        self._items = {}
        self._counter = 1001
        self._lock = threading.Lock()

    def add_item(self, item: ItemCreate):
        with self._lock:
            item_id = self._counter
            self._items[item_id] = item.model_dump()
            self._counter += 1
            logger.info(f"Added item_id={item_id} name={item.name} qty={item.quantity}")
            return {"id": item_id, **self._items[item_id]}

    def summary(self):
        with self._lock:
            total_val = sum(i["quantity"] * i["price"] for i in self._items.values())
            return {"total_skus": len(self._items), "total_valuation_usd": round(total_val, 2)}

store = ProductionInventoryStore()

@app.get("/health")
def health_check():
    uptime = round(time.time() - START_TIME, 2)
    logger.info("Health check probe succeeded")
    return {"status": "healthy", "environment": APP_ENV, "version": APP_VERSION, "uptime_sec": uptime}

@app.post("/api/v1/items", status_code=201)
def create_item(payload: ItemCreate):
    return store.add_item(payload)

@app.get("/api/v1/valuation")
def get_valuation():
    return store.summary()