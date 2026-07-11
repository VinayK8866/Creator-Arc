import os
import sys
import re
import asyncio
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

# Add backend directory to sys.path to access app modules
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "apps", "backend"))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.job import Job
from app.services.gemini_service import gemini_service

# Directory for storing temp files
UPLOAD_DIR = "/tmp/creator_arc_uploads" if os.name != 'nt' else "C:/temp/creator_arc_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def run_async(coro):
    return asyncio.run(coro)


def extract_video_id(url: str) -> str:
    """Extracts 11-character video ID from YouTube URL, or returns a hash for other media URLs."""
    import hashlib
    try:
        pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    except Exception:
        pass
        
    return hashlib.md5(url.encode()).hexdigest()


def fetch_transcript_safely(video_id: str) -> str:
    """Fetches video transcript, returning empty string if unavailable."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'es', 'fr', 'de'])
        return " ".join([item['text'] for item in transcript_list])
    except Exception:
        return ""


def download_youtube_audio(video_url: str, video_id: str) -> str:
    """Downloads audio track from YouTube video directly to .m4a/.webm format without FFmpeg conversion."""
    outtmpl_path = os.path.join(UPLOAD_DIR, f"audio_{video_id}.%(ext)s")
    
    # Check if file already exists in directory to avoid re-downloading
    for file in os.listdir(UPLOAD_DIR):
        if file.startswith(f"audio_{video_id}"):
            return os.path.join(UPLOAD_DIR, file)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': outtmpl_path,
        'quiet': True,
        'no_warnings': True,
        # Max file size 30MB (roughly 30-40 minutes of audio stream)
        'max_filesize': 30 * 1024 * 1024
    }

    print(f"Downloading YouTube audio track for {video_id}...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        filename = ydl.prepare_filename(info)
        
        # Double check filename resolves correctly (sometimes yt-dlp adjusts extensions)
        if os.path.exists(filename):
            return filename
            
        for file in os.listdir(UPLOAD_DIR):
            if file.startswith(f"audio_{video_id}"):
                return os.path.join(UPLOAD_DIR, file)
                
        raise FileNotFoundError("Downloaded YouTube audio stream path not found")


@celery_app.task(name="workers.tasks.youtube_tasks.summarize_video_task")
def summarize_video_task(job_id: str, video_url: str):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return

    audio_path = None
    try:
        job.status = "processing"
        db.commit()

        video_id = extract_video_id(video_url)
        transcript = fetch_transcript_safely(video_id)

        if not transcript:
            # Captions are disabled. Download audio and send to Gemini Multimodal API
            print(f"Captions disabled for {video_id}. Initializing audio download...")
            audio_path = download_youtube_audio(video_url, video_id)
            
            system_prompt = (
                "You are an expert audio summarizer. Listen carefully to the attached audio file. "
                "Write a highly detailed, professional, bullet-pointed summary "
                "of the spoken content. Group key takeaways under bold thematic headers."
            )
            summary = run_async(
                gemini_service.summarize_audio(
                    audio_path,
                    system_prompt,
                    "Provide a comprehensive summary of this audio recording."
                )
            )
            method = "multimodal_audio"
        else:
            # Captions retrieved successfully. Run normal text model
            system_prompt = (
                "You are an expert content summarizer. Write a highly detailed, professional, bullet-pointed summary "
                "of the provided YouTube video transcript. Group key takeaways under bold thematic headers."
            )
            summary = run_async(gemini_service._call_gemini(system_prompt, transcript))
            method = "transcript_text"

        job.status = "completed"
        job.result = {
            "summary": summary,
            "video_url": video_url,
            "video_id": video_id,
            "processing_method": method,
            "transcript_length": len(transcript) if transcript else 0
        }
        db.commit()

    except Exception as e:
        job.status = "failed"
        job.error = f"Summarization failed: {str(e)}"
        db.commit()
    finally:
        # Clean up local audio file if downloaded
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                print(f"Cleaned up local audio file: {audio_path}")
            except Exception as cleanup_err:
                print(f"Failed to remove local audio file: {str(cleanup_err)}")
        db.close()


@celery_app.task(name="workers.tasks.youtube_tasks.generate_tags_task")
def generate_tags_task(job_id: str, video_url: str):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return

    audio_path = None
    try:
        job.status = "processing"
        db.commit()

        video_id = extract_video_id(video_url)
        transcript = fetch_transcript_safely(video_id)

        system_prompt = (
            "You are a YouTube SEO keyword researcher. Based on the provided video content, "
            "generate exactly 15 highly optimized SEO search tags/keywords. Return ONLY a single, "
            "flat comma-separated list of these tags. Do not number them or add markdown formatting."
        )

        if not transcript:
            print(f"Captions disabled. Using multimodal audio analysis for tags...")
            audio_path = download_youtube_audio(video_url, video_id)
            tags_raw = run_async(
                gemini_service.summarize_audio(
                    audio_path,
                    system_prompt,
                    "Listen to this audio track and generate 15 SEO tags."
                )
            )
        else:
            user_input = f"Video URL: {video_url}\nTranscript Snippet: {transcript[:2000]}"
            tags_raw = run_async(gemini_service._call_gemini(system_prompt, user_input))

        tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()]

        job.status = "completed"
        job.result = {
            "tags": tags,
            "raw": tags_raw
        }
        db.commit()

    except Exception as e:
        job.status = "failed"
        job.error = f"Tag generation failed: {str(e)}"
        db.commit()
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except:
                pass
        db.close()


@celery_app.task(name="workers.tasks.youtube_tasks.generate_description_task")
def generate_description_task(job_id: str, video_url: str):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return

    audio_path = None
    try:
        job.status = "processing"
        db.commit()

        video_id = extract_video_id(video_url)
        transcript = fetch_transcript_safely(video_id)

        system_prompt = (
            "You are a professional YouTube description writer. Create an engaging, click-worthy video description "
            "based on the video transcript. It must contain: 1) a compelling hook, 2) a clear overview of "
            "what viewers will learn, and 3) placeholders for timestamps, links, and standard channel disclaimers."
        )

        if not transcript:
            print(f"Captions disabled. Using multimodal audio analysis for description...")
            audio_path = download_youtube_audio(video_url, video_id)
            description = run_async(
                gemini_service.summarize_audio(
                    audio_path,
                    system_prompt,
                    "Listen to this audio and write a YouTube video description."
                )
            )
        else:
            user_input = f"Video URL: {video_url}\nTranscript Snippet: {transcript[:2000]}"
            description = run_async(gemini_service._call_gemini(system_prompt, user_input))

        job.status = "completed"
        job.result = {
            "description": description
        }
        db.commit()

    except Exception as e:
        job.status = "failed"
        job.error = f"Description generation failed: {str(e)}"
        db.commit()
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except:
                pass
        db.close()
