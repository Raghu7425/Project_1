import asyncio
import random
import re
from typing import Any

from app.models.enums import JobType


async def document_ocr(payload: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(float(payload.get("duration", 1.5)))
    pages = int(payload.get("pages", random.randint(1, 80)))
    return {
        "document_uri": payload.get("document_uri", "s3://incoming/document.pdf"),
        "pages": pages,
        "language": payload.get("language", "en"),
        "ocr_confidence": round(random.uniform(0.88, 0.99), 3),
        "extracted_entities": payload.get("entities", ["invoice_number", "total", "due_date"]),
        "search_indexed": True,
        "artifact": f"documents/ocr/{random.randint(1000, 9999)}.json",
    }


async def media_transcode(payload: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(float(payload.get("duration", 1.0)))
    return {
        "source_uri": payload.get("source_uri", "s3://incoming/video.mp4"),
        "duration_seconds": float(payload.get("duration_seconds", 95.4)),
        "codec": payload.get("codec", "h264"),
        "container": payload.get("container", "mp4"),
        "renditions": payload.get("renditions", ["1080p", "720p", "480p"]),
        "thumbnail_uri": f"media/thumbs/{random.randint(1000, 9999)}.jpg",
        "manifest_uri": f"media/manifests/{random.randint(1000, 9999)}.m3u8",
    }


async def ai_summarization(payload: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(float(payload.get("duration", 2.0)))
    if payload.get("fail"):
        raise RuntimeError("simulated model provider timeout")
    text = str(payload.get("text", "Customer calls mention latency, onboarding friction, and positive support sentiment."))
    words = re.findall(r"\w+", text)
    return {
        "model": payload.get("model", "gpt-4.1-mini"),
        "input_tokens": max(len(words), 1),
        "summary": " ".join(words[: min(18, len(words))]) or "No text provided.",
        "topics": payload.get("topics", ["latency", "onboarding", "support"]),
        "sentiment": payload.get("sentiment", "mixed_positive"),
    }


async def content_moderation(payload: dict[str, Any]) -> dict[str, Any]:
    await asyncio.sleep(float(payload.get("duration", 0.8)))
    labels = payload.get("labels", {"violence": 0.01, "self_harm": 0.0, "adult": 0.03})
    flagged = any(float(score) >= 0.8 for score in labels.values())
    return {
        "asset_uri": payload.get("asset_uri", "s3://incoming/upload.jpg"),
        "flagged": flagged,
        "labels": labels,
        "action": "review" if flagged else "approve",
        "review_queue": "trust-and-safety" if flagged else None,
    }


PROCESSORS = {
    JobType.DOCUMENT_OCR.value: document_ocr,
    JobType.MEDIA_TRANSCODE.value: media_transcode,
    JobType.AI_SUMMARIZATION.value: ai_summarization,
    JobType.CONTENT_MODERATION.value: content_moderation,
}
