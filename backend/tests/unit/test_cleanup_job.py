"""
Fase 3 — job cleanup temp upload (docs/ARCHITECTURE.md §7). Dependency dimock.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.jobs import cleanup_temp_uploads as job


class _FakeSessionCtx:
    def __init__(self):
        self.commit = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


@pytest.mark.asyncio
async def test_run_memanggil_cleanup_dan_commit(monkeypatch):
    fake_session = _FakeSessionCtx()
    monkeypatch.setattr(job, "get_sessionmaker", lambda: (lambda: fake_session))
    monkeypatch.setattr(job, "build_r2_client", lambda: MagicMock())

    fake_service = MagicMock()
    fake_service.cleanup_expired = AsyncMock(return_value=3)
    monkeypatch.setattr(job, "UploadService", lambda **kw: fake_service)

    removed = await job.run()

    assert removed == 3
    fake_service.cleanup_expired.assert_awaited_once()
    fake_session.commit.assert_awaited_once()


def test_main_mencetak_hasil(monkeypatch, capsys):
    async def fake_run():
        return 5

    monkeypatch.setattr(job, "run", fake_run)
    job.main()

    assert "5" in capsys.readouterr().out
