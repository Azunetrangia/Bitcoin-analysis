"""
Cloudflare R2 Storage Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Infrastructure component for object storage using Cloudflare R2 (S3-compatible).

Why Cloudflare R2?
- 10x cheaper than AWS S3 ($0.015/GB/month vs $0.023/GB/month)
- ZERO egress fees (S3 charges $0.09/GB)
- S3-compatible API (use boto3)
- Global edge network (fast access)

Use Cases:
- Warm storage for historical data (3+ years)
- Backup and archival
- Data sharing (public URLs)
- DuckDB remote queries via HTTP
"""

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.shared.exceptions.custom_exceptions import StorageError
from src.shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class R2Client:
    """
    Client for Cloudflare R2 object storage.
    
    Configuration:
        R2_ACCOUNT_ID: Your Cloudflare account ID
        R2_ACCESS_KEY_ID: R2 access key
        R2_SECRET_ACCESS_KEY: R2 secret key
        R2_BUCKET_NAME: Bucket name
    
    Features:
        - Upload/download objects
        - List objects with prefix filtering
        - Generate public URLs
        - Multipart uploads for large files
        - Streaming downloads
    """
    
    def __init__(
        self,
        account_id: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str
    ):
        """
        Initialize R2 client.
        
        Args:
            account_id: Cloudflare account ID
            access_key_id: R2 access key ID
            secret_access_key: R2 secret access key
            bucket_name: R2 bucket name
        """
        self.account_id = account_id
        self.bucket_name = bucket_name
        
        # R2 endpoint format: https://<account_id>.r2.cloudflarestorage.com
        endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
        
        # Initialize boto3 S3 client with R2 endpoint
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",  # R2 uses "auto" region
        )
        
        # Transfer configuration for multipart uploads
        self.transfer_config = TransferConfig(
            multipart_threshold=1024 * 25,  # 25MB
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True
        )
        
        logger.info(
            f"✅ R2 client initialized",
            bucket=bucket_name,
            endpoint=endpoint_url
        )
    
    def upload_file(
        self,
        local_path: Path | str,
        object_key: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload file to R2.
        
        Args:
            local_path: Local file path
            object_key: Object key in R2 (e.g., 'btcusdt/1h/2024-01/data.parquet')
            metadata: Optional metadata dict
            content_type: Optional content type (auto-detected if None)
            
        Returns:
            Object key
            
        Example:
            >>> client = R2Client(...)
            >>> client.upload_file(
            ...     'data/processed/btcusdt/1h/2024-01/data.parquet',
            ...     'btcusdt/1h/2024-01/data.parquet',
            ...     metadata={'symbol': 'btcusdt', 'interval': '1h'}
            ... )
        """
        try:
            local_path = Path(local_path)
            
            if not local_path.exists():
                raise StorageError(f"Local file not found: {local_path}")
            
            # Auto-detect content type
            if content_type is None:
                if local_path.suffix == ".parquet":
                    content_type = "application/octet-stream"
                elif local_path.suffix == ".csv":
                    content_type = "text/csv"
                elif local_path.suffix == ".json":
                    content_type = "application/json"
                else:
                    content_type = "application/octet-stream"
            
            # Prepare extra args
            extra_args = {"ContentType": content_type}
            
            if metadata:
                extra_args["Metadata"] = metadata
            
            # Upload file
            file_size = local_path.stat().st_size / 1024 / 1024  # MB
            
            logger.info(
                f"📤 Uploading to R2",
                local_path=str(local_path),
                object_key=object_key,
                size_mb=f"{file_size:.2f}"
            )
            
            self.s3_client.upload_file(
                str(local_path),
                self.bucket_name,
                object_key,
                ExtraArgs=extra_args,
                Config=self.transfer_config
            )
            
            logger.info(f"✅ Upload complete", object_key=object_key)
            
            return object_key
            
        except ClientError as e:
            raise StorageError(
                f"R2 upload failed: {str(e)}",
                details={"object_key": object_key}
            )
    
    def download_file(
        self,
        object_key: str,
        local_path: Path | str
    ) -> Path:
        """
        Download file from R2.
        
        Args:
            object_key: Object key in R2
            local_path: Local destination path
            
        Returns:
            Local file path
        """
        try:
            local_path = Path(local_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"📥 Downloading from R2", object_key=object_key)
            
            self.s3_client.download_file(
                self.bucket_name,
                object_key,
                str(local_path),
                Config=self.transfer_config
            )
            
            file_size = local_path.stat().st_size / 1024 / 1024  # MB
            
            logger.info(
                f"✅ Download complete",
                local_path=str(local_path),
                size_mb=f"{file_size:.2f}"
            )
            
            return local_path
            
        except ClientError as e:
            raise StorageError(
                f"R2 download failed: {str(e)}",
                details={"object_key": object_key}
            )
    
    def list_objects(
        self,
        prefix: str = "",
        max_keys: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List objects in R2 bucket.
        
        Args:
            prefix: Filter by prefix (e.g., 'btcusdt/1h/')
            max_keys: Maximum number of objects to return
            
        Returns:
            List of object metadata dicts
            
        Example:
            >>> objects = client.list_objects(prefix='btcusdt/1h/')
            >>> for obj in objects:
            ...     print(obj['Key'], obj['Size'], obj['LastModified'])
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            if "Contents" not in response:
                return []
            
            objects = []
            
            for obj in response["Contents"]:
                objects.append({
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"],
                    "etag": obj["ETag"].strip('"')
                })
            
            logger.debug(
                f"📋 Listed {len(objects)} objects",
                prefix=prefix
            )
            
            return objects
            
        except ClientError as e:
            raise StorageError(
                f"R2 list failed: {str(e)}",
                details={"prefix": prefix}
            )
    
    def object_exists(self, object_key: str) -> bool:
        """
        Check if object exists in R2.
        
        Args:
            object_key: Object key
            
        Returns:
            True if exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
        except ClientError:
            return False
    
    def delete_object(self, object_key: str) -> bool:
        """
        Delete object from R2.
        
        Args:
            object_key: Object key
            
        Returns:
            True if deleted, False if not found
        """
        try:
            if not self.object_exists(object_key):
                return False
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            logger.info(f"🗑️ Deleted object", object_key=object_key)
            
            return True
            
        except ClientError as e:
            raise StorageError(
                f"R2 delete failed: {str(e)}",
                details={"object_key": object_key}
            )
    
    def delete_objects_by_prefix(self, prefix: str) -> int:
        """
        Delete all objects with given prefix.
        
        Args:
            prefix: Object key prefix
            
        Returns:
            Number of objects deleted
        """
        objects = self.list_objects(prefix=prefix)
        
        if not objects:
            return 0
        
        # Delete in batches (max 1000 per request)
        deleted_count = 0
        
        for i in range(0, len(objects), 1000):
            batch = objects[i:i+1000]
            
            delete_dict = {
                "Objects": [{"Key": obj["key"]} for obj in batch]
            }
            
            try:
                response = self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete=delete_dict
                )
                
                deleted_count += len(response.get("Deleted", []))
                
            except ClientError as e:
                raise StorageError(
                    f"R2 batch delete failed: {str(e)}",
                    details={"prefix": prefix}
                )
        
        logger.info(
            f"🗑️ Deleted {deleted_count} objects",
            prefix=prefix
        )
        
        return deleted_count
    
    def get_public_url(
        self,
        object_key: str,
        custom_domain: Optional[str] = None
    ) -> str:
        """
        Get public URL for object.
        
        Args:
            object_key: Object key
            custom_domain: Optional custom domain (e.g., 'data.example.com')
            
        Returns:
            Public URL
            
        Note:
            Bucket must be configured for public access.
            
        Example:
            >>> url = client.get_public_url('btcusdt/1h/2024-01/data.parquet')
            >>> # https://<bucket>.r2.dev/btcusdt/1h/2024-01/data.parquet
        """
        if custom_domain:
            return f"https://{custom_domain}/{object_key}"
        else:
            # Default R2 public URL format
            return f"https://{self.bucket_name}.r2.dev/{object_key}"
    
    def get_presigned_url(
        self,
        object_key: str,
        expiration: int = 3600
    ) -> str:
        """
        Generate presigned URL for temporary access.
        
        Args:
            object_key: Object key
            expiration: URL expiration in seconds (default: 1 hour)
            
        Returns:
            Presigned URL
            
        Example:
            >>> url = client.get_presigned_url('private/data.parquet', expiration=7200)
            >>> # URL valid for 2 hours
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": object_key
                },
                ExpiresIn=expiration
            )
            
            logger.debug(
                f"🔗 Generated presigned URL",
                object_key=object_key,
                expiration=expiration
            )
            
            return url
            
        except ClientError as e:
            raise StorageError(
                f"Failed to generate presigned URL: {str(e)}",
                details={"object_key": object_key}
            )
    
    def get_object_metadata(self, object_key: str) -> Dict[str, Any]:
        """
        Get object metadata.
        
        Args:
            object_key: Object key
            
        Returns:
            Metadata dict
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            return {
                "size": response["ContentLength"],
                "last_modified": response["LastModified"],
                "content_type": response.get("ContentType"),
                "etag": response["ETag"].strip('"'),
                "metadata": response.get("Metadata", {})
            }
            
        except ClientError as e:
            raise StorageError(
                f"Failed to get metadata: {str(e)}",
                details={"object_key": object_key}
            )
