"""Teammates can import the real API without starting DB/Gmail lifecycle work."""

import asyncio

import httpx


def test_api_health_and_schema_import_without_starting_lifespan():
    from odin.api.main import app

    async def exercise():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")
            assert response.status_code == 200 and response.json() == {"ok": True}
            schema = await client.get("/openapi.json")
            assert schema.status_code == 200 and "/api/ask" in schema.json()["paths"]

    asyncio.run(exercise())
