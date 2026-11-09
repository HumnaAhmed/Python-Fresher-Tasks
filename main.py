from typing import Dict, List

class InventoryManager:

    def __init__(self):
        self.__items: Dict[int, Dict] = {}  # Encapsulated dictionary storage
        self.__counter = 1000

    def add_item(self, name: str, quantity: int, price: float) -> int:
        if quantity < 0 or price < 0:
            raise ValueError("[ERROR] Quantity and price must be non-negative values.")
        item_id = self.__counter
        self.__items[item_id] = {"name": name, "quantity": quantity, "price": price}
        self.__counter += 1
        print(f"[SUCCESS] Added item '{name}' with ID {item_id}")
        return item_id

    def get_inventory_valuation(self) -> float:
        total_value = sum(item["quantity"] * item["price"] for item in self.__items.values())
        print(f"[VALUATION] Total Inventory Asset Value: ${total_value:.2f}")
        return total_value


if __name__ == "__main__":
    print("=== TASK 3: PRACTICAL IMPLEMENTATION PROJECT ===")
    manager = InventoryManager()

    manager.add_item("Dell Latitude 5430 Laptop", 5, 850.00)
    manager.add_item("Wireless Mechanical Keyboard", 15, 45.50)
    manager.add_item("USB-C Docking Station", 8, 120.00)

    manager.get_inventory_valuation()
    print("=== PRACTICAL IMPLEMENTATION COMPLETED SUCCESSFULLY ===")