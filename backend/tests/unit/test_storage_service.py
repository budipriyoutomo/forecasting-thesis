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


def _konfigurasi_s3(monkeypatch, **override):
    """Isi settings S3 dengan nilai valid; `override` menimpa per-test."""
    from app.config import get_settings

    settings = get_settings()
    nilai = {
        "S3_ENDPOINT_URL": "https://is3.cloudhost.id",
        "S3_ACCESS_KEY": "key",
        "S3_SECRET_KEY": "secret",
        "S3_REGION": "SouthJkt-a",
        "S3_ADDRESSING_STYLE": "auto",
        **override,
    }
    for nama, value in nilai.items():
        monkeypatch.setattr(settings, nama, value)
    return settings


def _fake_boto3(monkeypatch):
    sentinel = object()
    fake = MagicMock()
    fake.client.return_value = sentinel
    monkeypatch.setitem(__import__("sys").modules, "boto3", fake)
    return fake, sentinel


@pytest.mark.parametrize("kosong", ["S3_ENDPOINT_URL", "S3_ACCESS_KEY"])
def test_build_s3_client_belum_dikonfigurasi_raise(monkeypatch, kosong):
    from app.services.storage_service import build_s3_client

    _konfigurasi_s3(monkeypatch, **{kosong: None})

    with pytest.raises(StorageUploadFailedError):
        build_s3_client()


def test_build_s3_client_pakai_endpoint_dan_region_dari_settings(monkeypatch):
    """Endpoint & region dibaca dari env — bukan hardcode ke provider tertentu."""
    from app.services import storage_service

    _konfigurasi_s3(monkeypatch)
    fake_boto3, sentinel = _fake_boto3(monkeypatch)

    assert storage_service.build_s3_client() is sentinel
    call = fake_boto3.client.call_args
    assert call.args[0] == "s3"
    assert call.kwargs["endpoint_url"] == "https://is3.cloudhost.id"
    assert call.kwargs["region_name"] == "SouthJkt-a"
    assert call.kwargs["aws_access_key_id"] == "key"
    assert call.kwargs["aws_secret_access_key"] == "secret"


def test_build_s3_client_addressing_style_path_diteruskan_ke_config(monkeypatch):
    """S3_ADDRESSING_STYLE=path dipakai kalau provider tak punya wildcard DNS bucket."""
    from app.services import storage_service

    _konfigurasi_s3(monkeypatch, S3_ADDRESSING_STYLE="path")
    fake_boto3, _ = _fake_boto3(monkeypatch)

    storage_service.build_s3_client()

    config = fake_boto3.client.call_args.kwargs["config"]
    assert config.s3["addressing_style"] == "path"
    assert config.signature_version == "s3v4"
