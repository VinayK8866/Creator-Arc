import os
import sys
import urllib.request
from PIL import Image, ImageFilter
from rembg import remove

# Add backend directory to sys.path to access app modules
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "apps", "backend"))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

import asyncio
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.job import Job
from app.services.storage_service import storage_service
from app.services.gemini_service import gemini_service
from workers.tasks.youtube_tasks import download_youtube_audio, extract_video_id

# Directory for saving outputs locally before uploading
UPLOAD_DIR = "/tmp/creator_arc_uploads" if os.name != 'nt' else "C:/temp/creator_arc_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _load_image(payload: dict) -> (Image.Image, str):
    """Loads image from local path or downloads from URL."""
    local_path = payload.get("local_path")
    if local_path and os.path.exists(local_path):
        return Image.open(local_path), local_path

    image_url = payload.get("image_url")
    if not image_url:
        raise Exception("No image source provided in payload")

    # Download image from URL
    temp_filename = f"downloaded_{os.urandom(8).hex()}.png"
    temp_path = os.path.join(UPLOAD_DIR, temp_filename)
    urllib.request.urlretrieve(image_url, temp_path)
    return Image.open(temp_path), temp_path


@celery_app.task(name="workers.tasks.media_tasks.upscale_image_task")
def upscale_image_task(job_id: str, payload: dict):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return

    try:
        job.status = "processing"
        db.commit()

        # Load image
        img, source_path = _load_image(payload)

        # Local High-Quality Upscale (supports multi-choice: 2x, 3x, 4x)
        scale = int(payload.get("scale", 2))
        if scale not in [2, 3, 4]:
            scale = 2  # Sanitize to default 2x

        new_size = (img.width * scale, img.height * scale)
        upscaled_img = img.resize(new_size, resample=Image.Resampling.LANCZOS)
        
        # Apply unsharp mask to restore edge definitions
        sharpened_img = upscaled_img.filter(
            ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=2)
        )

        output_filename = f"upscaled_{job_id}.png"
        output_path = os.path.join(UPLOAD_DIR, output_filename)
        sharpened_img.save(output_path, format="PNG")

        # Upload to cloud storage (falls back to local static serve automatically)
        output_url = storage_service.upload_file(output_path, output_filename)

        # Save success status
        job.status = "completed"
        job.result = {
            "output_url": output_url,
            "filename": output_filename,
            "scale": f"{scale}x",
            "original_size": f"{img.width}x{img.height}",
            "new_size": f"{new_size[0]}x{new_size[1]}"
        }
        db.commit()

    except Exception as e:
        job.status = "failed"
        job.error = f"Upscaling failed: {str(e)}"
        db.commit()
    finally:
        db.close()


@celery_app.task(name="workers.tasks.media_tasks.remove_bg_task")
def remove_bg_task(job_id: str, payload: dict):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return

    try:
        job.status = "processing"
        db.commit()

        # Load image
        img, source_path = _load_image(payload)

        # Local background removal using rembg (runs locally on U-2-Net model)
        no_bg_img = remove(img)

        output_filename = f"nobg_{job_id}.png"
        output_path = os.path.join(UPLOAD_DIR, output_filename)
        no_bg_img.save(output_path, format="PNG")

        # Upload to cloud storage
        output_url = storage_service.upload_file(output_path, output_filename)

        job.status = "completed"
        job.result = {
            "output_url": output_url,
            "filename": output_filename,
            "mode": no_bg_img.mode
        }
        db.commit()

    except Exception as e:
        job.status = "failed"
        job.error = f"Background removal failed: {str(e)}"
        db.commit()
    finally:
        db.close()


@celery_app.task(name="workers.tasks.media_tasks.transcribe_link_task")
def transcribe_link_task(job_id: str, media_url: str):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return

    audio_path = None
    try:
        job.status = "processing"
        db.commit()

        # Step 1: Download audio via yt-dlp
        link_id = extract_video_id(media_url)
        audio_path = download_youtube_audio(media_url, link_id)

        # Step 2: Feed directly into Gemini multimodal API
        system_prompt = (
            "You are an expert audio transcriptionist and summarizer. Listen carefully to the attached audio track. "
            "You must generate two sections in your response:\n\n"
            "## TRANSCRIPT\n"
            "Provide a faithful, complete, and word-for-word text transcription of the spoken audio.\n\n"
            "## SUMMARY\n"
            "Provide a comprehensive, professional, structured, bullet-pointed summary of the main points and key takeaways."
        )

        print(f"Media Tasks: Sending audio {audio_path} to Gemini Multimodal API...")
        result_text = asyncio.run(
            gemini_service.summarize_audio(
                audio_path,
                system_prompt,
                "Transcribe and summarize this audio recording completely."
            )
        )

        # Step 3: Update job status
        job.status = "completed"
        job.result = {
            "media_url": media_url,
            "link_id": link_id,
            "raw_markdown": result_text
        }
        db.commit()

    except Exception as e:
        job.status = "failed"
        job.error = f"Media transcription failed: {str(e)}"
        db.commit()
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                print(f"Media Tasks: Cleaned up local file: {audio_path}")
            except Exception as cleanup_err:
                print(f"Media Tasks: Failed to remove local file: {str(cleanup_err)}")
        db.close()

