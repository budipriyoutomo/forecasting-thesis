"""
Fase 3 — job cleanup temp upload (docs/ARCHITECTURE.md §7). Dependency dimock.
"""
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest

from app.jobs import cleanup_temp_uploads as job
from app.services.upload_service import UploadService


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
    monkeypatch.setattr(job, "build_s3_client", lambda: MagicMock())

    # autospec, BUKAN `lambda **kw`: konstruktor palsu yang menelan keyword apa pun
    # membuat drift signature UploadService lolos tanpa ketahuan (job ini pernah
    # tertinggal saat rename v3.0 consumptions/materials → demand/products).
    fake_cls = create_autospec(UploadService)
    fake_service = fake_cls.return_value
    fake_service.cleanup_expired = AsyncMock(return_value=3)
    monkeypatch.setattr(job, "UploadService", fake_cls)

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
