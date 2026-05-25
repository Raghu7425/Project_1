import asyncio
import csv
import random
from pathlib import Path
from typing import Any

from app.models.enums import JobType


def _extract_inventory_from_file(file_path: str) -> list[dict[str, Any]]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"inventory file not found: {path}")

    if path.suffix.lower() != ".csv":
        raise ValueError(f"unsupported inventory extension: {path.suffix}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = csv.DictReader(file)
        return [
            {
                "sku": row.get("sku") or row.get("SKU"),
                "expected": int(row.get("expected") or row.get("Expected") or 0),
                "counted": int(row.get("counted") or row.get("Counted") or row.get("expected") or 0),
            }
            for row in rows
        ]


def _line_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return list(payload.get("items", []))


def _order_totals(items: list[dict[str, Any]]) -> tuple[int, float]:
    units = sum(int(item.get("quantity", 1)) for item in items)
    subtotal = sum(float(item.get("unit_price", 0)) * int(item.get("quantity", 1)) for item in items)
    return units, round(subtotal, 2)


async def order_fulfillment(payload: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(float(payload.get("duration", 1.2)))
    items = _line_items(payload)
    units, subtotal = _order_totals(items)
    shipping_method = payload.get("shipping_method", "standard")
    return {
        "order_id": payload.get("order_id", f"ORD-{random.randint(1000, 9999)}"),
        "customer": payload.get("customer", "Guest customer"),
        "items_reserved": [{"sku": item.get("sku"), "quantity": item.get("quantity", 1)} for item in items],
        "units": units,
        "subtotal": subtotal,
        "tax": round(subtotal * float(payload.get("tax_rate", 0.08)), 2),
        "shipping_method": shipping_method,
        "fulfillment_status": "ready_to_ship",
        "tracking_number": f"SHOP{random.randint(100000, 999999)}",
    }


async def inventory_recount(payload: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(float(payload.get("duration", 1.0)))
    products = (
        await asyncio.to_thread(_extract_inventory_from_file, str(payload["file_path"]))
        if payload.get("file_path")
        else list(payload.get("products", []))
    )
    adjustments = []
    for product in products:
        expected = int(product.get("expected", 0))
        counted = int(product.get("counted", expected))
        adjustments.append(
            {
                "sku": product.get("sku"),
                "expected": expected,
                "counted": counted,
                "delta": counted - expected,
            }
        )
    return {
        "warehouse": payload.get("warehouse", "main"),
        "products_checked": len(products),
        "adjustments": adjustments,
        "requires_review": any(abs(item["delta"]) >= 5 for item in adjustments),
        "audit_id": f"INV-{random.randint(1000, 9999)}",
    }


async def restock_alert(payload: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(float(payload.get("duration", 0.8)))
    if payload.get("fail"):
        raise RuntimeError("simulated supplier API timeout")
    products = list(payload.get("products", []))
    alerts = []
    for product in products:
        stock = int(product.get("stock", 0))
        reorder_point = int(product.get("reorder_point", 10))
        if stock <= reorder_point:
            alerts.append(
                {
                    "sku": product.get("sku"),
                    "stock": stock,
                    "reorder_point": reorder_point,
                    "suggested_order": max(int(product.get("target_stock", 50)) - stock, 0),
                }
            )
    return {
        "supplier": payload.get("supplier", "default-supplier"),
        "alerts_created": len(alerts),
        "alerts": alerts,
        "purchase_order_draft": f"PO-{random.randint(1000, 9999)}" if alerts else None,
    }


async def sales_report(payload: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(float(payload.get("duration", 1.4)))
    orders = list(payload.get("orders", []))
    revenue = round(sum(float(order.get("total", 0)) for order in orders), 2)
    return {
        "period": payload.get("period", "today"),
        "orders": len(orders),
        "revenue": revenue,
        "average_order_value": round(revenue / len(orders), 2) if orders else 0,
        "top_skus": payload.get("top_skus", ["BAG-001", "TEE-204", "MUG-110"]),
        "export_uri": f"reports/sales/{random.randint(1000, 9999)}.json",
    }


PROCESSORS = {
    JobType.ORDER_FULFILLMENT.value: order_fulfillment,
    JobType.INVENTORY_RECOUNT.value: inventory_recount,
    JobType.RESTOCK_ALERT.value: restock_alert,
    JobType.SALES_REPORT.value: sales_report,
}
