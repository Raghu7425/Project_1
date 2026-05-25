import argparse
import asyncio

import httpx


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email", default="demo@example.com")
    parser.add_argument("--password", default="password123")
    args = parser.parse_args()

    async with httpx.AsyncClient(base_url=args.base_url, timeout=10) as client:
        register = await client.post("/api/v1/auth/register", json={"email": args.email, "password": args.password})
        if register.status_code == 409:
            token = (await client.post("/api/v1/auth/login", json={"email": args.email, "password": args.password})).json()["access_token"]
        else:
            register.raise_for_status()
            token = register.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        jobs = [
            {"job_type": "document_ocr", "payload": {"pages": 32}, "priority": 1, "idempotency_key": "demo-ocr-1"},
            {"job_type": "media_transcode", "payload": {"source_uri": "s3://bucket/video.mov"}, "priority": 4},
            {"job_type": "ai_summarization", "payload": {"fail": True}, "priority": 2, "max_retries": 2},
            {"job_type": "content_moderation", "payload": {"labels": {"adult": 0.92}}, "priority": 8},
        ]
        for job in jobs:
            response = await client.post("/api/v1/jobs", json=job, headers=headers)
            response.raise_for_status()
            print(response.json())


if __name__ == "__main__":
    asyncio.run(main())
