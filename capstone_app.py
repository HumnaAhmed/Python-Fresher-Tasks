import os
import time
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from capstone_service import InventoryAnalyticsEngine

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler("capstone_prod.log"), logging.StreamHandler()]
)
logger = logging.getLogger("ScaleCoreAPI")

app = FastAPI(title="ScaleCore Inventory & Analytics API", version="2.0.0")
engine = InventoryAnalyticsEngine(os.getenv("DB_PATH", "scalecore_prod.db"))
BOOT_TIME = time.time()

class ProductPayload(BaseModel):
    sku: str = Field(..., min_length=3, max_length=32)
    name: str = Field(..., min_length=2, max_length=100)
    category: str = Field(..., min_length=2, max_length=50)
    stock_qty: int = Field(..., ge=0)
    unit_price: float = Field(..., ge=0.0)
    reorder_threshold: int = Field(default=5, ge=0)

class StockDeltaPayload(BaseModel):
    delta: int
    reason: str = "ORDER_FULFILLMENT"

@app.get("/health")
def health_probe():
    return {"status": "healthy", "version": "2.0.0", "uptime_sec": round(time.time() - BOOT_TIME, 2)}

@app.post("/api/v2/products", status_code=201)
def create_product(body: ProductPayload):
    try:
        res = engine.register_product(**body.model_dump())
        logger.info(f"Registered SKU={res['sku']} qty={res['stock_qty']}")
        return res
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

@app.patch("/api/v2/products/{sku}/stock")
def update_stock(sku: str, body: StockDeltaPayload):
    try:
        res = engine.adjust_stock(sku, body.delta, body.reason)
        logger.info(f"Adjusted SKU={sku} delta={body.delta} new_qty={res['stock_qty']}")
        return res
    except KeyError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=409, detail=str(err))

@app.get("/api/v2/analytics")
def analytics_overview():
    return engine.get_analytics_summary()