import argparse
import asyncio
import random
import uuid

import httpx


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--jobs", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=25)
    args = parser.parse_args()

    async with httpx.AsyncClient(base_url=args.base_url, timeout=20) as client:
        email = f"load-{uuid.uuid4()}@example.com"
        token = (await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        sem = asyncio.Semaphore(args.concurrency)

        async def submit(i: int) -> int:
            async with sem:
                body = {
                    "job_type": random.choice(["pdf_processing", "image_resize", "email_sending", "report_generation"]),
                    "payload": {"duration": 0.05, "index": i},
                    "priority": random.randint(1, 10),
                    "idempotency_key": f"load-{i}",
                }
                response = await client.post("/api/v1/jobs", json=body, headers=headers)
                return response.status_code

        statuses = await asyncio.gather(*(submit(i) for i in range(args.jobs)))
        print({status: statuses.count(status) for status in sorted(set(statuses))})


if __name__ == "__main__":
    asyncio.run(main())
