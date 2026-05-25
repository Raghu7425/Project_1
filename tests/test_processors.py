import asyncio

import pytest

from app.worker.processors import ai_summarization, content_moderation, document_ocr, media_transcode


def test_processors_return_realistic_results():
    async def run() -> tuple[dict, dict, dict]:
        return await asyncio.gather(
            document_ocr({"duration": 0, "pages": 3}),
            media_transcode({"duration": 0, "renditions": ["720p"]}),
            content_moderation({"duration": 0, "labels": {"adult": 0.1}}),
        )

    ocr, media, moderation = asyncio.run(run())

    assert ocr["pages"] == 3
    assert media["renditions"] == ["720p"]
    assert moderation["action"] == "approve"


def test_ai_processor_can_simulate_provider_failure():
    with pytest.raises(RuntimeError):
        asyncio.run(ai_summarization({"duration": 0, "fail": True}))
