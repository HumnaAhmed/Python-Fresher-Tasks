import pytest
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from capstone_service import InventoryAnalyticsEngine
from capstone_app import app

@pytest.fixture
def service():
    eng = InventoryAnalyticsEngine(":memory:")
    yield eng
    eng.close()

def test_unit_reject_negative_stock(service):
    with pytest.raises(ValueError, match="non-negative"):
        service.register_product("BAD-01", "Invalid Item", "Test", -5, 10.0)

def test_integration_api_lifecycle():
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

def test_concurrency_50_threads(service):
    service.register_product("LAP-900", "Workstation Pro", "Hardware", 100, 1200.0, 10)
    with ThreadPoolExecutor(max_workers=25) as pool:
        list(pool.map(lambda _: service.adjust_stock("LAP-900", -1, "LOAD_TEST"), range(50)))
    assert service.get_product("LAP-900")["stock_qty"] == 50

def test_system_e2e_valuation_and_alert(service):
    service.register_product("MON-100", "4K Display", "Monitors", 6, 300.0, reorder_threshold=5)
    assert service.get_analytics_summary()["low_stock_alerts"] == 0
    service.adjust_stock("MON-100", -2, "CUSTOMER_ORDER")
    summary = service.get_analytics_summary()
    assert summary["low_stock_alerts"] == 1
    assert summary["total_valuation_usd"] == 1200.0