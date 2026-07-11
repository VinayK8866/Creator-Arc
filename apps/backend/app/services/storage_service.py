import os
import shutil
import boto3
from botocore.client import Config
from app.core.config import settings

class StorageService:
    def __init__(self):
        self.s3_configured = all([
            settings.S3_ACCESS_KEY_ID,
            settings.S3_SECRET_ACCESS_KEY,
            settings.S3_BUCKET_NAME
        ])
        
        if self.s3_configured:
            # Configure boto3 client to support cloud providers like R2 and Supabase
            self.s3_client = boto3.client(
                's3',
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
                config=Config(signature_version='s3v4')
            )
            self.bucket_name = settings.S3_BUCKET_NAME
        else:
            self.s3_client = None
            self.bucket_name = None

    def upload_file(self, local_path: str, filename: str) -> str:
        """Uploads file to cloud storage bucket, falling back to local static serving if S3 is not set."""
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")
            
        if self.s3_configured:
            try:
                # Determine Content-Type
                content_type = "image/png"
                if filename.endswith(".jpg") or filename.endswith(".jpeg"):
                    content_type = "image/jpeg"
                elif filename.endswith(".mp3") or filename.endswith(".m4a"):
                    content_type = "audio/mpeg"

                # Upload to S3
                self.s3_client.upload_file(
                    local_path,
                    self.bucket_name,
                    filename,
                    ExtraArgs={
                        'ContentType': content_type
                    }
                )
                
                # Construct public endpoint URL
                # If endpoint is custom (e.g. Cloudflare R2 or Supabase)
                if settings.S3_ENDPOINT_URL:
                    # e.g., https://[id].r2.cloudflarestorage.com/bucket/filename
                    # Usually, public access uses a custom domain or standard structure
                    # We will return the S3-API URL, or custom layout if it's Supabase
                    if "supabase" in settings.S3_ENDPOINT_URL:
                        # Supabase storage public url layout:
                        # https://[project-ref].supabase.co/storage/v1/object/public/[bucket]/[filename]
                        project_url = settings.S3_ENDPOINT_URL.replace("/storage/v1/s3", "")
                        return f"{project_url}/storage/v1/object/public/{self.bucket_name}/{filename}"
                    
                    # Default custom endpoint URL
                    endpoint = settings.S3_ENDPOINT_URL.rstrip('/')
                    return f"{endpoint}/{self.bucket_name}/{filename}"
                else:
                    return f"https://{self.bucket_name}.s3.amazonaws.com/{filename}"
            except Exception as e:
                # Log error and fallback to local
                print(f"Cloud upload failed, falling back to local: {str(e)}")
                
        # Fallback local file copying
        dest_dir = "/tmp/creator_arc_uploads" if os.name != 'nt' else "C:/temp/creator_arc_uploads"
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, filename)
        
        # Avoid self-copying if the source is already in the dest directory
        if os.path.abspath(local_path) != os.path.abspath(dest_path):
            shutil.copy2(local_path, dest_path)
            
        return f"http://localhost:8000/static/{filename}"

storage_service = StorageService()
