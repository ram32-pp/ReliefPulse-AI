import os
import uuid
from pathlib import Path
from typing import BinaryIO
from app.config import settings

# Attempt to import oss2 for Alibaba Cloud OSS
try:
    import oss2
    OSS_AVAILABLE = True
except ImportError:
    OSS_AVAILABLE = False


class StorageService:
    """
    Storage service supporting Alibaba Cloud OSS with automatic local fallback.
    Uploads audio, images, and video clips for emergency SOS reports.
    """

    def __init__(self):
        self.oss_bucket = None
        self.is_oss_configured = False
        self._init_oss()

    def _init_oss(self):
        if not OSS_AVAILABLE:
            print("[StorageService] Note: oss2 package not loaded, using local storage fallback.")
            return

        ak_id = settings.alibaba_oss_access_key_id.strip()
        ak_secret = settings.alibaba_oss_access_key_secret.strip()
        endpoint = settings.alibaba_oss_endpoint.strip()
        bucket_name = settings.alibaba_oss_bucket_name.strip()

        if ak_id and ak_secret and endpoint and bucket_name:
            try:
                auth = oss2.Auth(ak_id, ak_secret)
                # Clean endpoint format if needed
                clean_endpoint = endpoint.replace("https://", "").replace("http://", "").strip("/")
                self.oss_bucket = oss2.Bucket(auth, f"https://{clean_endpoint}", bucket_name)
                self.is_oss_configured = True
                self.endpoint_host = clean_endpoint
                self.bucket_name = bucket_name
                print(f"[StorageService] Alibaba Cloud OSS connected: bucket={bucket_name}")
            except Exception as e:
                print(f"[StorageService] Failed to initialize Alibaba Cloud OSS ({e}), using local fallback.")
                self.is_oss_configured = False
        else:
            print("[StorageService] Alibaba Cloud OSS credentials not fully configured; using local storage fallback.")

    async def upload_bytes(
        self,
        data: bytes,
        original_filename: str = "media.bin",
        content_type: str = "application/octet-stream",
        folder: str = "reports",
    ) -> str:
        """
        Uploads raw binary bytes to Alibaba Cloud OSS or local disk.
        Returns the publicly accessible URL string.
        """
        extension = Path(original_filename).suffix or ".bin"
        unique_name = f"{uuid.uuid4().hex[:12]}{extension}"
        object_key = f"{folder}/{unique_name}"

        # 1. Try Alibaba Cloud OSS if configured
        if self.is_oss_configured and self.oss_bucket:
            try:
                headers = {"Content-Type": content_type}
                self.oss_bucket.put_object(object_key, data, headers=headers)
                # Construct public OSS URL
                oss_url = f"https://{self.bucket_name}.{self.endpoint_host}/{object_key}"
                print(f"[StorageService] Uploaded to Alibaba Cloud OSS: {oss_url}")
                return oss_url
            except Exception as e:
                print(f"[StorageService] OSS upload error ({e}), falling back to local disk.")

        # 2. Local disk fallback
        local_dir = Path(settings.media_upload_dir) / folder
        local_dir.mkdir(parents=True, exist_ok=True)
        file_path = local_dir / unique_name

        with open(file_path, "wb") as f:
            f.write(data)

        local_url = f"/uploads/{folder}/{unique_name}"
        print(f"[StorageService] Saved locally: {local_url}")
        return local_url


storage_service = StorageService()
