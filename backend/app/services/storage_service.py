"""S3-compatible file storage service (works with MinIO in dev)."""

import asyncio
import uuid
from datetime import datetime, timezone

import structlog
import boto3
from botocore.exceptions import ClientError

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class StorageService:
    """S3-compatible object storage service."""

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        region: str = "us-east-1",
    ):
        self.endpoint = endpoint or settings.s3_endpoint
        self.access_key = access_key or settings.s3_access_key
        self.secret_key = secret_key or settings.s3_secret_key
        self.bucket = bucket or settings.s3_bucket
        self.region = region

        self._client = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )
        self._bucket_ensured = False

    async def _ensure_bucket(self) -> None:
        """Create the bucket if it doesn't exist."""
        if self._bucket_ensured:
            return
        try:
            await asyncio.to_thread(self._client.head_bucket, Bucket=self.bucket)
        except ClientError:
            try:
                await asyncio.to_thread(
                    self._client.create_bucket, Bucket=self.bucket
                )
                logger.info("bucket_created", bucket=self.bucket)
            except ClientError as e:
                if "BucketAlreadyOwnedByYou" not in str(e):
                    logger.error("bucket_create_failed", error=str(e))
                    raise
        self._bucket_ensured = True

    async def upload_file(
        self,
        file_bytes: bytes,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a file and return the access URL.

        Args:
            file_bytes: File content.
            key: Object key (path within bucket).
            content_type: MIME type.

        Returns:
            URL to access the file.
        """
        await self._ensure_bucket()

        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )

        url = f"{self.endpoint}/{self.bucket}/{key}"
        logger.info("file_uploaded", key=key, size=len(file_bytes), content_type=content_type)
        return url

    async def download_file(self, key: str) -> bytes:
        """Download file content by key.

        Args:
            key: Object key.

        Returns:
            File content as bytes.

        Raises:
            FileNotFoundError: If the key doesn't exist.
        """
        try:
            response = await asyncio.to_thread(
                self._client.get_object, Bucket=self.bucket, Key=key
            )
            body = await asyncio.to_thread(response["Body"].read)
            return body
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {key}")
            raise

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a pre-signed download URL.

        Args:
            key: Object key.
            expires_in: URL expiry in seconds (default 1 hour).

        Returns:
            Pre-signed URL string.
        """
        url = await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url

    async def delete_file(self, key: str) -> bool:
        """Delete a file by key.

        Args:
            key: Object key.

        Returns:
            True if successful.
        """
        try:
            await asyncio.to_thread(
                self._client.delete_object, Bucket=self.bucket, Key=key
            )
            logger.info("file_deleted", key=key)
            return True
        except ClientError as e:
            logger.error("file_delete_failed", key=key, error=str(e))
            return False

    async def list_files(self, prefix: str = "") -> list[dict]:
        """List files in the bucket with an optional prefix.

        Args:
            prefix: Key prefix to filter by (e.g. "tender/project-123/").

        Returns:
            List of file info dicts: [{"key", "size", "last_modified"}].
        """
        try:
            response = await asyncio.to_thread(
                self._client.list_objects_v2,
                Bucket=self.bucket,
                Prefix=prefix,
                MaxKeys=1000,
            )
            files = []
            for obj in response.get("Contents", []):
                files.append({
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                })
            return files
        except ClientError as e:
            logger.error("list_files_failed", prefix=prefix, error=str(e))
            return []

    @staticmethod
    def generate_key(project_id: str, filename: str, category: str = "tender") -> str:
        """Generate a unique object key.

        Format: {category}/{project_id}/{timestamp}_{uuid8}_{filename}

        Args:
            project_id: Project UUID.
            filename: Original file name.
            category: File category (tender / output / quotation).

        Returns:
            Unique key string.
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        short_id = uuid.uuid4().hex[:8]
        # Sanitize filename
        safe_name = "".join(c if c.isalnum() or c in ".-_" else "_" for c in filename)
        return f"{category}/{project_id}/{ts}_{short_id}_{safe_name}"


# ── Singleton ──

_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
