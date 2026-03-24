import abc
import asyncio
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

class AudioStorageBackend(abc.ABC):
    """All storage backends implement this interface."""

    @abc.abstractmethod
    async def exists(self, path: str) -> bool:
        """Return True if a file at this path already exists."""

    @abc.abstractmethod
    async def upload(self, data: bytes, path: str, content_type: str) -> str:
        """
        Store audio bytes at `path`.
        Returns the full public URL the client can fetch.
        """

class LocalAudioBackend(AudioStorageBackend):
    """
    Writes MP3 files to a local folder and serves them via FastAPI static mount.
    """

    def __init__(self):
        self.base_dir = Path(settings.AUDIO_LOCAL_DIR)
        self.base_url = settings.AUDIO_LOCAL_BASE_URL.rstrip("/")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _full_path(self, path: str) -> Path:
        return self.base_dir / path

    async def exists(self, path: str) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._full_path(path).exists)

    async def upload(self, data: bytes, path: str, content_type: str) -> str:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._write_file, path, data)
        return f"{self.base_url}/audio/{path}"

    def _write_file(self, path: str, data: bytes) -> None:
        full_path = self._full_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)

class R2AudioBackend(AudioStorageBackend):
    """
    Uploads MP3 files to Cloudflare R2 (S3-compatible API).
    """

    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
        self.bucket = settings.R2_BUCKET_NAME
        self.public_url = settings.R2_PUBLIC_URL.rstrip("/")

    async def exists(self, path: str) -> bool:
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: self.client.head_object(Bucket=self.bucket, Key=path),
            )
            return True
        except ClientError:
            return False

    async def upload(self, data: bytes, path: str, content_type: str) -> str:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._put_object, path, data, content_type)
        return f"{self.public_url}/{path}"

    def _put_object(self, path: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=path,
            Body=data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )

def _make_backend() -> AudioStorageBackend:
    backend = getattr(settings, "AUDIO_STORAGE_BACKEND", "local").lower()
    if backend == "r2" and settings.R2_ENDPOINT_URL:
        return R2AudioBackend()
    return LocalAudioBackend()

# Module-level singleton imported by TTSService
audio_storage: AudioStorageBackend = _make_backend()
