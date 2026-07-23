"""
Fase 0 — health check endpoint (docs/TASK_BREAKDOWN.md).

Kriteria selesai Fase 0: health check endpoint jalan dan responsenya mengikuti
envelope standar AGENTS.md §4 supaya frontend bisa memakai API client yang sama
seperti endpoint lain.
"""
import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    res = await client.get("/health")

    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_health_tidak_butuh_token(client):
    """Health check dipakai monitoring/uptime check — tidak boleh butuh auth."""
    res = await client.get("/health")

    assert res.status_code == 200


@pytest.mark.asyncio
async def test_health_menyertakan_versi_dan_env(client):
    """Berguna untuk memastikan deploy mana yang sedang jalan (Railway/lokal)."""
    body = (await client.get("/health")).json()

    assert body["data"]["version"]
    assert body["data"]["environment"]
