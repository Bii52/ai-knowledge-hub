"""Storage client module for downloading documents from Supabase S3 / MinIO."""

import io
import logging
from typing import Optional
from botocore.config import Config
from botocore.exceptions import ClientError
import boto3

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class StorageException(Exception):
    """Base exception for storage operations."""
    pass


class StorageFileNotFoundException(StorageException):
    """Exception raised when an object is not found in storage."""
    pass


class S3StorageClient:
    """Client for interacting with S3-compatible object storage (Supabase S3 / MinIO)."""

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> None:
        """Initialize the S3 client with credentials.

        Args:
            endpoint_url: Endpoint URL for S3 API.
            access_key: S3 Access Key ID.
            secret_key: S3 Secret Access Key.
            region: AWS Region name.
            bucket_name: S3 bucket name.
        """
        settings = get_settings()
        self.endpoint_url = endpoint_url or settings.STORAGE_ENDPOINT_URL
        self.access_key = access_key or settings.STORAGE_ACCESS_KEY
        self.secret_key = secret_key or settings.STORAGE_SECRET_KEY
        self.region = region or settings.STORAGE_REGION
        self.bucket_name = bucket_name or settings.STORAGE_BUCKET_NAME

        # Force path-style addressing for MinIO and Supabase S3
        config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            retries={"max_attempts": 3, "mode": "standard"},
        )

        client_kwargs = {
            "service_name": "s3",
            "region_name": self.region,
            "config": config,
        }

        if self.endpoint_url:
            client_kwargs["endpoint_url"] = self.endpoint_url
        if self.access_key and self.secret_key:
            client_kwargs["aws_access_key_id"] = self.access_key
            client_kwargs["aws_secret_access_key"] = self.secret_key

        self._s3_client = boto3.client(**client_kwargs)

    def download_file(self, storage_path: str) -> bytes:
        """Download a file from storage and return its raw byte content.

        Args:
            storage_path: Relative storage path/key of the file.

        Returns:
            Raw bytes of the file content.

        Raises:
            StorageFileNotFoundException: If file does not exist in bucket.
            StorageException: On other S3 client errors.
        """
        if not storage_path or not storage_path.strip():
            raise ValueError("storage_path cannot be empty.")

        # Clean leading slashes
        normalized_key = storage_path.lstrip("/")

        try:
            logger.info("Downloading file from S3: bucket=%s, key=%s", self.bucket_name, normalized_key)
            response = self._s3_client.get_object(
                Bucket=self.bucket_name,
                Key=normalized_key,
            )
            body = response["Body"]
            return body.read()
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404", "NotFound"):
                logger.error("File not found in storage: %s", normalized_key)
                raise StorageFileNotFoundException(
                    f"File '{normalized_key}' not found in storage bucket '{self.bucket_name}'."
                ) from exc

            logger.error("S3 ClientError downloading file %s: %s", normalized_key, exc)
            raise StorageException(f"Failed to download file '{normalized_key}' from storage: {exc}") from exc
        except Exception as exc:
            logger.error("Unexpected error downloading file %s: %s", normalized_key, exc)
            raise StorageException(f"Unexpected error downloading file '{normalized_key}': {exc}") from exc


_storage_client: Optional[S3StorageClient] = None


def get_storage_client() -> S3StorageClient:
    """Singleton getter for S3StorageClient."""
    global _storage_client
    if _storage_client is None:
        _storage_client = S3StorageClient()
    return _storage_client

