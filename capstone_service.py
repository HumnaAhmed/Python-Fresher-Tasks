import sqlite3
import threading
import time
from functools import lru_cache
from typing import Dict

class InventoryAnalyticsEngine:
    """Thread-safe, SQLite WAL-backed Inventory & Order Analytics Engine."""

    def __init__(self, db_path: str = "scalecore_prod.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._cache_epoch = 0
        self._conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA synchronous=NORMAL;")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    sku TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    stock_qty INTEGER NOT NULL CHECK(stock_qty >= 0),
                    unit_price REAL NOT NULL CHECK(unit_price >= 0.0),
                    reorder_threshold INTEGER NOT NULL DEFAULT 5
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stock_ledger (
                    tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sku TEXT NOT NULL,
                    delta INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    timestamp REAL NOT NULL
                );
            """)
            self._conn.commit()

    def _invalidate_cache(self) -> None:
        self._cache_epoch += 1
        self._cached_valuation.cache_clear()

    def register_product(self, sku: str, name: str, category: str,
                         stock_qty: int, unit_price: float, reorder_threshold: int = 5) -> Dict:
        if not sku or not sku.strip():
            raise ValueError("SKU identifier cannot be empty.")
        if stock_qty < 0 or unit_price < 0:
            raise ValueError("Stock quantity and unit price must be non-negative.")
        norm_sku = sku.strip().upper()
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("BEGIN IMMEDIATE;")
            try:
                cur.execute(
                    "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?)",
                    (norm_sku, name.strip(), category.strip(), stock_qty, round(unit_price, 2), reorder_threshold)
                )
                cur.execute(
                    "INSERT INTO stock_ledger (sku, delta, reason, timestamp) VALUES (?, ?, ?, ?)",
                    (norm_sku, stock_qty, "INITIAL_STOCK", time.time())
                )
                self._conn.commit()
                self._invalidate_cache()
            except sqlite3.IntegrityError as exc:
                self._conn.rollback()
                raise ValueError(f"Duplicate SKU detected: {norm_sku}") from exc
        return self.get_product(norm_sku)

    def adjust_stock(self, sku: str, delta: int, reason: str = "ORDER_FULFILLMENT") -> Dict:
        norm_sku = sku.strip().upper()
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("BEGIN IMMEDIATE;")
            try:
                cur.execute("SELECT stock_qty FROM products WHERE sku = ?", (norm_sku,))
                row = cur.fetchone()
                if row is None:
                    raise KeyError(f"SKU not found: {norm_sku}")
                new_qty = row["stock_qty"] + delta
                if new_qty < 0:
                    raise ValueError(f"Insufficient stock for {norm_sku}")
                cur.execute("UPDATE products SET stock_qty = ? WHERE sku = ?", (new_qty, norm_sku))
                cur.execute(
                    "INSERT INTO stock_ledger (sku, delta, reason, timestamp) VALUES (?, ?, ?, ?)",
                    (norm_sku, delta, reason, time.time())
                )
                self._conn.commit()
                self._invalidate_cache()
            except Exception:
                self._conn.rollback()
                raise
        return self.get_product(norm_sku)

    def get_product(self, sku: str) -> Dict:
        norm_sku = sku.strip().upper()
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM products WHERE sku = ?", (norm_sku,))
            row = cur.fetchone()
            if row is None:
                raise KeyError(f"SKU not found: {norm_sku}")
            return dict(row)

    @lru_cache(maxsize=32)
    def _cached_valuation(self, epoch: int) -> Dict:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT stock_qty, unit_price, reorder_threshold FROM products")
            rows = cur.fetchall()
            total_value = round(sum(r["stock_qty"] * r["unit_price"] for r in rows), 2)
            low_stock = sum(1 for r in rows if r["stock_qty"] <= r["reorder_threshold"])
            return {"total_skus": len(rows), "total_valuation_usd": total_value, "low_stock_alerts": low_stock}

    def get_analytics_summary(self) -> Dict:
        return self._cached_valuation(self._cache_epoch)

    def close(self) -> None:
        with self._lock:
            self._conn.close()