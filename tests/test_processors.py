import asyncio

import pytest

from app.worker.processors import inventory_recount, order_fulfillment, restock_alert, sales_report


def test_processors_return_realistic_results():
    async def run() -> tuple[dict, dict, dict]:
        return await asyncio.gather(
            order_fulfillment(
                {
                    "duration": 0,
                    "items": [{"sku": "BAG-001", "quantity": 2, "unit_price": 24.99}],
                }
            ),
            inventory_recount(
                {
                    "duration": 0,
                    "products": [{"sku": "MUG-110", "expected": 42, "counted": 36}],
                }
            ),
            sales_report({"duration": 0, "orders": [{"total": 25}, {"total": 75}]}),
        )

    order, inventory, report = asyncio.run(run())

    assert order["units"] == 2
    assert inventory["adjustments"][0]["delta"] == -6
    assert report["average_order_value"] == 50


def test_restock_processor_can_simulate_supplier_failure():
    with pytest.raises(RuntimeError):
        asyncio.run(restock_alert({"duration": 0, "fail": True}))


def test_inventory_processor_imports_csv_file(tmp_path):
    inventory = tmp_path / "inventory.csv"
    inventory.write_text(
        "sku,expected,counted\n"
        "BAG-001,120,118\n"
        "MUG-110,42,36\n",
        encoding="utf-8",
    )

    result = asyncio.run(inventory_recount({"duration": 0, "file_path": str(inventory)}))

    assert result["products_checked"] == 2
    assert result["adjustments"][0]["sku"] == "BAG-001"
    assert result["requires_review"] is True
