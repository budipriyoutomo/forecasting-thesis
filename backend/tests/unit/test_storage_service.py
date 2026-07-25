"""
Fase 3 — StorageService dengan client S3 (R2) di-mock (tanpa R2 nyata).
"""
from unittest.mock import MagicMock

import pytest

from app.services.storage_service import StorageService
from app.utils.exceptions import StorageUploadFailedError


def _svc(client=None):
    return StorageService(client or MagicMock(), bucket="test-bucket")


def test_upload_temp_menaruh_di_prefix_temp():
    client = MagicMock()
    svc = _svc(client)

    key = svc.upload_temp("sess-1", "data.csv", b"abc")

    assert key == "temp/uploads/sess-1/data.csv"
    args = client.put_object.call_args.kwargs
    assert args["Bucket"] == "test-bucket"
    assert args["Key"] == "temp/uploads/sess-1/data.csv"
    assert args["Body"] == b"abc"


def test_upload_export_menaruh_di_prefix_exports():
    client = MagicMock()
    svc = _svc(client)

    key = svc.upload_export("user-1", "run-9", "reorder_run-9.pdf", b"%PDF")

    assert key == "permanent/exports/user-1/run-9/reorder_run-9.pdf"
    args = client.put_object.call_args.kwargs
    assert args["Key"] == "permanent/exports/user-1/run-9/reorder_run-9.pdf"
    assert args["Body"] == b"%PDF"


def test_move_to_permanent_copy_lalu_hapus_temp():
    client = MagicMock()
    svc = _svc(client)

    dst = svc.move_to_permanent("user-9", "sess-1", "data.csv")

    assert dst == "permanent/datasets/user-9/sess-1/raw.csv"
    client.copy_object.assert_called_once()
    client.delete_object.assert_called_once()


def test_upload_gagal_dibungkus_storage_error():
    client = MagicMock()
    client.put_object.side_effect = RuntimeError("network down")
    svc = _svc(client)

    with pytest.raises(StorageUploadFailedError):
        svc.upload_temp("sess-1", "data.csv", b"abc")


def test_move_gagal_dibungkus_storage_error():
    client = MagicMock()
    client.copy_object.side_effect = RuntimeError("boom")
    svc = _svc(client)

    with pytest.raises(StorageUploadFailedError):
        svc.move_to_permanent("user-9", "sess-1", "data.csv")


def test_delete_temp():
    client = MagicMock()
    svc = _svc(client)

    svc.delete_temp("sess-1", "data.csv")

    client.delete_object.assert_called_once()


def test_delete_temp_gagal_dibungkus_storage_error():
    client = MagicMock()
    client.delete_object.side_effect = RuntimeError("boom")
    svc = _svc(client)

    with pytest.raises(StorageUploadFailedError):
        svc.delete_temp("sess-1", "data.csv")


def test_build_r2_client_belum_dikonfigurasi_raise(monkeypatch):
    from app.config import get_settings
    from app.services.storage_service import build_r2_client

    settings = get_settings()
    monkeypatch.setattr(settings, "CLOUDFLARE_R2_ACCOUNT_ID", None)
    monkeypatch.setattr(settings, "CLOUDFLARE_R2_ACCESS_KEY", None)

    with pytest.raises(StorageUploadFailedError):
        build_r2_client()


def test_build_r2_client_terkonfigurasi_membuat_client(monkeypatch):
    from app.config import get_settings
    from app.services import storage_service

    settings = get_settings()
    monkeypatch.setattr(settings, "CLOUDFLARE_R2_ACCOUNT_ID", "acc")
    monkeypatch.setattr(settings, "CLOUDFLARE_R2_ACCESS_KEY", "key")
    monkeypatch.setattr(settings, "CLOUDFLARE_R2_SECRET_KEY", "secret")

    sentinel = object()
    fake_boto3 = MagicMock()
    fake_boto3.client.return_value = sentinel
    monkeypatch.setitem(__import__("sys").modules, "boto3", fake_boto3)

    assert storage_service.build_r2_client() is sentinel
    assert fake_boto3.client.call_args.args[0] == "s3"
