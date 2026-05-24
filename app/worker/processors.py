import asyncio
import random
from typing import Any

from app.models.enums import JobType


async def process_pdf(payload: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(float(payload.get("duration", 1.5)))
    pages = int(payload.get("pages", random.randint(1, 80)))
    return {"pages": pages, "text_indexed": True, "artifact": f"pdf/{random.randint(1000, 9999)}.json"}


async def resize_image(payload: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(float(payload.get("duration", 1.0)))
    return {
        "source": payload.get("source", "unknown"),
        "width": int(payload.get("width", 1280)),
        "height": int(payload.get("height", 720)),
        "format": payload.get("format", "webp"),
    }


async def send_email(payload: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(float(payload.get("duration", 0.5)))
    if payload.get("to") == "fail@example.com":
        raise RuntimeError("simulated mail provider rejection")
    return {"provider_message_id": f"msg_{random.randint(100000, 999999)}"}


async def generate_report(payload: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(float(payload.get("duration", 2.0)))
    return {"rows": int(payload.get("rows", 1000)), "artifact": "reports/latest.csv"}


PROCESSORS = {
    JobType.PDF_PROCESSING.value: process_pdf,
    JobType.IMAGE_RESIZE.value: resize_image,
    JobType.EMAIL_SENDING.value: send_email,
    JobType.REPORT_GENERATION.value: generate_report,
}
