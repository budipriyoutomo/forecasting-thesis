"""
StorageService — object storage S3-compatible, docs/ARCHITECTURE.md §7.

Struktur:
  temp/uploads/{session_id}/{filename}          ← TTL 1 jam sebelum divalidasi
  permanent/datasets/{user_id}/{session_id}/raw.csv

Provider ditentukan sepenuhnya lewat env (`S3_ENDPOINT_URL` dkk) — service ini
hanya memakai operasi S3 standar (put/copy/delete), jadi Cloudflare R2,
IDCloudHost, MinIO, atau AWS S3 sama-sama jalan tanpa perubahan kode.

Client S3 (boto3) injectable supaya bisa dites tanpa storage nyata. Kalau belum
dikonfigurasi, `build_s3_client()` raise error jelas. Semua kegagalan storage
dibungkus jadi STORAGE_UPLOAD_FAILED (tanpa bocorkan detail internal, AGENTS.md §10 #4).
"""
from app.config import get_settings
from app.utils.exceptions import AppError, StorageUploadFailedError


def _temp_key(session_id: str, filename: str) -> str:
    return f"temp/uploads/{session_id}/{filename}"


def _permanent_key(user_id: str, session_id: str) -> str:
    return f"permanent/datasets/{user_id}/{session_id}/raw.csv"


def _export_key(user_id: str, run_id: str, filename: str) -> str:
    return f"permanent/exports/{user_id}/{run_id}/{filename}"


def build_s3_client():
    """Bangun client boto3 S3 dari settings. Raise kalau belum dikonfigurasi."""
    settings = get_settings()
    if not settings.S3_ENDPOINT_URL or not settings.S3_ACCESS_KEY:
        raise StorageUploadFailedError("Object storage belum dikonfigurasi (S3_ENDPOINT_URL/S3_ACCESS_KEY).")

    import boto3  # import lokal — boto3 hanya perlu saat storage benar-benar dipakai
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        # signature_version dipatok s3v4: R2 & IDCloudHost sama-sama menolak s2.
        config=Config(
            s3={"addressing_style": settings.S3_ADDRESSING_STYLE},
            signature_version="s3v4",
        ),
    )


class StorageService:
    def __init__(self, client, bucket: str | None = None):
        self._client = client
        self._bucket = bucket or get_settings().S3_BUCKET_NAME

    def upload_temp(self, session_id: str, filename: str, content: bytes) -> str:
        key = _temp_key(session_id, filename)
        self._put(key, content)
        return key

    def move_to_permanent(self, user_id: str, session_id: str, filename: str) -> str:
        """Copy temp → permanent lalu hapus temp (S3 tidak punya operasi move atomik)."""
        src = _temp_key(session_id, filename)
        dst = _permanent_key(user_id, session_id)
        try:
            self._client.copy_object(
                Bucket=self._bucket, CopySource={"Bucket": self._bucket, "Key": src}, Key=dst
            )
            self._client.delete_object(Bucket=self._bucket, Key=src)
        except AppError:
            raise
        except Exception as exc:
            raise StorageUploadFailedError("Gagal memindahkan file ke penyimpanan permanen.") from exc
        return dst

    def upload_export(self, user_id: str, run_id: str, filename: str, content: bytes) -> str:
        key = _export_key(user_id, run_id, filename)
        self._put(key, content)
        return key

    def delete_temp(self, session_id: str, filename: str) -> None:
        key = _temp_key(session_id, filename)
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except Exception as exc:  # cleanup tidak boleh menggagalkan proses lain
            raise StorageUploadFailedError("Gagal menghapus file temp.") from exc

    def _put(self, key: str, content: bytes) -> None:
        try:
            self._client.put_object(Bucket=self._bucket, Key=key, Body=content)
        except Exception as exc:
            raise StorageUploadFailedError("Gagal mengunggah file ke penyimpanan.") from exc
