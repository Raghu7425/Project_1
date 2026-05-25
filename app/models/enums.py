from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class JobType(StrEnum):
    ORDER_FULFILLMENT = "order_fulfillment"
    INVENTORY_RECOUNT = "inventory_recount"
    RESTOCK_ALERT = "restock_alert"
    SALES_REPORT = "sales_report"
