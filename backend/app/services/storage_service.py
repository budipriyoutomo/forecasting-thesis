"""
StorageService — Cloudflare R2 (S3-compatible), docs/ARCHITECTURE.md §7.

Struktur:
  temp/uploads/{session_id}/{filename}          ← TTL 1 jam sebelum divalidasi
  permanent/datasets/{user_id}/{session_id}/raw.csv

Client S3 (boto3) injectable supaya bisa dites tanpa R2 nyata. Kalau R2 belum
dikonfigurasi, `build_r2_client()` raise error jelas. Semua kegagalan ke R2
dibungkus jadi STORAGE_UPLOAD_FAILED (tanpa bocorkan detail internal, AGENTS.md §10 #4).
"""
from app.config import get_settings
from app.utils.exceptions import AppError, StorageUploadFailedError


def _temp_key(session_id: str, filename: str) -> str:
    return f"temp/uploads/{session_id}/{filename}"


def _permanent_key(user_id: str, session_id: str) -> str:
    return f"permanent/datasets/{user_id}/{session_id}/raw.csv"


def build_r2_client():
    """Bangun client boto3 S3 untuk R2 dari settings. Raise kalau belum dikonfigurasi."""
    settings = get_settings()
    if not settings.CLOUDFLARE_R2_ACCOUNT_ID or not settings.CLOUDFLARE_R2_ACCESS_KEY:
        raise StorageUploadFailedError("Cloudflare R2 belum dikonfigurasi.")

    import boto3  # import lokal — boto3 hanya perlu saat R2 benar-benar dipakai

    endpoint = f"https://{settings.CLOUDFLARE_R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY,
        aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET_KEY,
        region_name="auto",
    )


class StorageService:
    def __init__(self, client, bucket: str | None = None):
        self._client = client
        self._bucket = bucket or get_settings().CLOUDFLARE_R2_BUCKET_NAME

    def upload_temp(self, session_id: str, filename: str, content: bytes) -> str:
        key = _temp_key(session_id, filename)
        self._put(key, content)
        return key

    def move_to_permanent(self, user_id: str, session_id: str, filename: str) -> str:
        """Copy temp → permanent lalu hapus temp (R2 tidak punya operasi move atomik)."""
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
