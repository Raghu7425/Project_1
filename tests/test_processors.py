import pytest

from app.worker.processors import generate_report, resize_image, send_email


@pytest.mark.asyncio
async def test_processors_return_realistic_results():
    image = await resize_image({"duration": 0, "width": 320, "height": 240})
    report = await generate_report({"duration": 0, "rows": 42})

    assert image["format"] == "webp"
    assert report["rows"] == 42


@pytest.mark.asyncio
async def test_email_processor_can_simulate_provider_failure():
    with pytest.raises(RuntimeError):
        await send_email({"duration": 0, "to": "fail@example.com"})
