import pytest

class InventoryManager:
    def __init__(self):
        self.items = {}
        self._counter = 1

    def add_item(self, name: str, qty: int, price: float):
        if qty < 0 or price < 0:
            raise ValueError("Quantity and price cannot be negative.")
        item_id = self._counter
        self.items[item_id] = {"name": name, "qty": qty, "price": price}
        self._counter += 1
        return item_id

    def get_total_valuation(self) -> float:
        return sum(item["qty"] * item["price"] for item in self.items.values())

@pytest.fixture
def inventory():
    return InventoryManager()

def test_add_item_success(inventory):
    item_id = inventory.add_item("Dell Latitude 5430", 3, 850.0)
    assert item_id == 1
    assert inventory.items[1]["name"] == "Dell Latitude 5430"

def test_add_item_negative_values(inventory):
    with pytest.raises(ValueError, match="Quantity and price cannot be negative."):
        inventory.add_item("Faulty Mouse", -1, 20.0)

def test_inventory_valuation(inventory):
    inventory.add_item("Keyboard", 2, 45.0)
    inventory.add_item("Monitor", 1, 150.0)
    assert inventory.get_total_valuation() == 240.0