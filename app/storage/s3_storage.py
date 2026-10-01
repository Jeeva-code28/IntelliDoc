import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Union, BinaryIO
from app.config import settings

logger = logging.getLogger("project_npn")


class S3ObjectStorage:
    """
    S3/MinIO Compatible Object Storage Service.
    Enforces multi-tenant storage paths: s3://npn-uploads/{tenant_id}/{document_id}.pdf
    Includes automatic fallback to local disk storage when S3/MinIO server is unconfigured.
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        bucket_name: str = "npn-uploads",
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None
    ):
        self.endpoint_url = endpoint_url or os.getenv("S3_ENDPOINT_URL")
        self.bucket_name = bucket_name
        self.access_key = access_key or os.getenv("S3_ACCESS_KEY", "minioadmin")
        self.secret_key = secret_key or os.getenv("S3_SECRET_KEY", "minioadmin")
        self.s3_client = None
        self._init_s3()

    def _init_s3(self) -> None:
        if not self.endpoint_url:
            logger.info("S3 endpoint not provided. Operating in Local Object Storage mode.")
            return

        try:
            import boto3
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key
            )
            # Ensure bucket exists
            buckets = [b["Name"] for b in self.s3_client.list_buckets().get("Buckets", [])]
            if self.bucket_name not in buckets:
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            logger.info(f"Connected to S3/MinIO object storage at {self.endpoint_url}, bucket '{self.bucket_name}'")
        except Exception as e:
            logger.warning(f"S3/MinIO connection failed ({e}). Falling back to Local Disk Object Storage.")
            self.s3_client = None

    def upload_file(
        self,
        file_obj_or_path: Union[str, Path, BinaryIO],
        document_id: str,
        filename: str,
        tenant_id: str = "default_tenant"
    ) -> str:
        """Uploads file to s3://npn-uploads/{tenant_id}/{document_id}.pdf and returns S3 URI or path."""
        s3_key = f"{tenant_id}/{document_id}_{filename}"
        s3_uri = f"s3://{self.bucket_name}/{s3_key}"

        if self.s3_client:
            try:
                if isinstance(file_obj_or_path, (str, Path)):
                    self.s3_client.upload_file(str(file_obj_or_path), self.bucket_name, s3_key)
                else:
                    self.s3_client.upload_fileobj(file_obj_or_path, self.bucket_name, s3_key)
                logger.info(f"Uploaded object to S3: {s3_uri}")
                return s3_uri
            except Exception as e:
                logger.error(f"S3 upload error ({e}). Writing to local storage fallback.")

        # Local storage fallback
        tenant_dir = settings.UPLOADS_DIR / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        local_path = tenant_dir / f"{document_id}_{filename}"

        if isinstance(file_obj_or_path, (str, Path)):
            shutil.copy(str(file_obj_or_path), str(local_path))
        else:
            with open(local_path, "wb") as out_buf:
                shutil.copyfileobj(file_obj_or_path, out_buf)

        return str(local_path)

    def download_file(self, s3_uri_or_path: str, dest_path: Union[str, Path]) -> str:
        """Downloads object from S3 or copies from local storage."""
        if s3_uri_or_path.startswith("s3://"):
            parts = s3_uri_or_path.replace("s3://", "").split("/", 1)
            bucket = parts[0]
            key = parts[1]
            if self.s3_client:
                self.s3_client.download_file(bucket, key, str(dest_path))
                return str(dest_path)

        if Path(s3_uri_or_path).exists():
            shutil.copy(s3_uri_or_path, str(dest_path))
            return str(dest_path)

        raise FileNotFoundError(f"Storage object not found: {s3_uri_or_path}")


_s3_storage = None


def get_s3_storage() -> S3ObjectStorage:
    global _s3_storage
    if _s3_storage is None:
        _s3_storage = S3ObjectStorage()
    return _s3_storage
