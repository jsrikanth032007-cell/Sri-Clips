import os
import re
import json
import time
import shutil
import threading
import yt_dlp
from faster_whisper import WhisperModel
import analyzer
import media_processor

# Global job status store
JOBS = {}
JOBS_LOCK = threading.Lock()

BASE_STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "temp_storage"))
CACHE_DIR = os.path.join(BASE_STORAGE_DIR, "_transcript_cache")
os.makedirs(BASE_STORAGE_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# In-memory Whisper model cache
WHISPER_MODELS = {}
WHISPER_LOCK = threading.Lock()


def get_faster_whisper_model(accuracy_mode: str = "balanced") -> tuple[WhisperModel, str]:
    """
    Loads faster-whisper model dynamically based on accuracy mode.
    Maps:
      - fast -> base
      - balanced -> small (default)
      - high_accuracy -> medium
    Auto-detects CUDA device, fallback to CPU with int8 quantization.
    """
    model_size_map = {
        "fast": "base",
        "balanced": "small",
        "high_accuracy": "medium"
    }
    model_size = model_size_map.get(accuracy_mode, "small")

    with WHISPER_LOCK:
        if model_size in WHISPER_MODELS:
            return WHISPER_MODELS[model_size], model_size

        print(f"Loading faster-whisper model '{model_size}'...")
        device = "cpu"
        compute_type = "int8"

        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
                compute_type = "float16"
        except Exception:
            pass

        try:
            model = WhisperModel(model_size, device=device, compute_type=compute_type)
            WHISPER_MODELS[model_size] = model
            print(f"faster-whisper '{model_size}' loaded on {device} ({compute_type}).")
            return model, model_size
        except Exception as e:
            print(f"Failed loading CUDA/float16 model, falling back to CPU int8: {e}")
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            WHISPER_MODELS[model_size] = model
            return model, model_size


def update_job(job_id: str, stage: str = None, progress: int = None, message: str = None, 
               error: str = None, clips: list = None, video_title: str = None, 
               video_duration: float = None, eta_seconds: int = None, quality_badge: str = None):
    with JOBS_LOCK:
        if job_id not in JOBS:
            return
        if stage is not None:
            JOBS[job_id]["stage"] = stage
        if progress is not None:
            JOBS[job_id]["progress"] = progress
        if message is not None:
            JOBS[job_id]["message"] = message
        if error is not None:
            JOBS[job_id]["error"] = error
            JOBS[job_id]["stage"] = "error"
        if clips is not None:
            JOBS[job_id]["clips"] = clips
        if video_title is not None:
            JOBS[job_id]["video_title"] = video_title
        if video_duration is not None:
            JOBS[job_id]["video_duration"] = video_duration
        if eta_seconds is not None:
            JOBS[job_id]["eta_seconds"] = eta_seconds
        if quality_badge is not None:
            JOBS[job_id]["quality_badge"] = quality_badge


def schedule_auto_cleanup(job_dir: str, delay_seconds: int = 3600):
    """Deletes job directory after delay_seconds (1 hour)."""
    def cleanup():
        time.sleep(delay_seconds)
        if os.path.exists(job_dir):
            try:
                shutil.rmtree(job_dir)
                print(f"Auto-cleaned temporary folder: {job_dir}")
            except Exception as e:
                print(f"Cleanup error for {job_dir}: {e}")

    t = threading.Thread(target=cleanup, daemon=True)
    t.start()


def extract_video_id(url: str) -> str:
    """Extracts YouTube video ID from URL or returns a hash."""
    match = re.search(r"(?:v=|\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})", url)
    if match:
        return match.group(1)
    import hashlib
    return hashlib.md5(url.encode('utf-8')).hexdigest()[:11]


def format_timestamp(seconds: float) -> str:
    """Formats float seconds to MM:SS string."""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def get_cache_file(video_id: str, model_size: str) -> str:
    return os.path.join(CACHE_DIR, f"{video_id}_{model_size}.json")


def load_cached_transcript(video_id: str, model_size: str):
    cache_file = get_cache_file(video_id, model_size)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"Loaded transcript from cache: {cache_file}")
                return data
        except Exception as e:
            print(f"Error reading transcript cache: {e}")
    return None


def save_cached_transcript(video_id: str, model_size: str, segments: list):
    cache_file = get_cache_file(video_id, model_size)
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)
            print(f"Saved transcript to cache: {cache_file}")
    except Exception as e:
        print(f"Error saving transcript cache: {e}")


def transcribe_with_faster_whisper(job_id: str, audio_path: str, video_id: str, accuracy_mode: str) -> list:
    """
    Transcribes audio using faster-whisper with live ETA progress & 90s stall timeout.
    Auto-retries once on stall/error.
    """
    model, model_size = get_faster_whisper_model(accuracy_mode)

    # Check cache first
    cached = load_cached_transcript(video_id, model_size)
    if cached:
        update_job(job_id, progress=55, message="Loaded cached AI transcription instantly!")
        return cached

    attempt = 0
    max_attempts = 2
    last_exception = None

    while attempt < max_attempts:
        attempt += 1
        try:
            if attempt > 1:
                update_job(job_id, message="Transcription stalled. Retrying transcription attempt 2/2...")
                time.sleep(1)

            print(f"Starting faster-whisper transcription (Attempt {attempt}/{max_attempts})...")
            segments_gen, info = model.transcribe(audio_path, beam_size=5)
            total_duration = info.duration if info and info.duration > 0 else 1.0

            formatted_segments = []
            start_wall_time = time.time()
            last_activity_time = time.time()

            for segment in segments_gen:
                current_time = time.time()
                # Check stall timeout (> 90 seconds without a new segment)
                if current_time - last_activity_time > 90:
                    raise TimeoutError("Transcription stalled for >90 seconds without progress.")
                
                last_activity_time = current_time

                end_sec = float(segment.end)
                formatted_segments.append({
                    "start": float(segment.start),
                    "end": end_sec,
                    "text": segment.text.strip()
                })

                # Calculate progress and ETA
                progress_pct = 25 + int((min(end_sec, total_duration) / total_duration) * 30)
                elapsed_wall = current_time - start_wall_time
                if end_sec > 0 and elapsed_wall > 0:
                    speed = end_sec / elapsed_wall
                    remaining_audio = max(0.0, total_duration - end_sec)
                    eta_sec = int(remaining_audio / speed) if speed > 0 else 0
                else:
                    eta_sec = 0

                processed_str = format_timestamp(end_sec)
                total_str = format_timestamp(total_duration)
                eta_str = f"~{eta_sec}s" if eta_sec > 0 else "estimating..."

                update_job(
                    job_id,
                    stage="transcribing",
                    progress=min(55, progress_pct),
                    message=f"Transcribing speech... {processed_str} / {total_str} processed (ETA: {eta_str})",
                    eta_seconds=eta_sec
                )

            # Save successful transcription to cache
            save_cached_transcript(video_id, model_size, formatted_segments)
            return formatted_segments

        except Exception as e:
            last_exception = e
            print(f"Transcription attempt {attempt} failed: {e}")

    raise Exception(f"Transcription failed after {max_attempts} attempts: {last_exception}")


def build_yt_dlp_format(quality: str) -> tuple[str, str]:
    """
    Returns yt-dlp format selector string and label badge.
    Options: 360p, 480p, 720p (default), 1080p, best
    """
    if quality == "360p":
        return "bestvideo[ext=mp4][height<=360]+bestaudio[ext=m4a]/best[ext=mp4][height<=360]/best", "360p SD"
    elif quality == "480p":
        return "bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/best[ext=mp4][height<=480]/best", "480p SD"
    elif quality == "1080p":
        return "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]/best", "1080p FHD"
    elif quality == "best":
        return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "Best Quality"
    else: # 720p default
        return "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/best", "720p HD"


def run_pipeline(job_id: str, youtube_url: str, quality: str = "720p", num_clips: int = 10, accuracy_mode: str = "balanced"):
    job_dir = os.path.join(BASE_STORAGE_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    source_video_path = os.path.join(job_dir, "source.mp4")
    output_wav_path = os.path.join(job_dir, "audio.wav")

    ffmpeg_exe = media_processor.get_ffmpeg_path()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe) if os.path.isabs(ffmpeg_exe) else None
    if ffmpeg_dir and ffmpeg_dir not in os.environ["PATH"]:
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]

    video_id = extract_video_id(youtube_url)
    format_selector, quality_badge = build_yt_dlp_format(quality)

    update_job(job_id, quality_badge=quality_badge)

    try:
        # STEP 1: Download YouTube Video
        update_job(
            job_id,
            stage="downloading",
            progress=10,
            message=f"Downloading YouTube video ({quality_badge})..."
        )

        ydl_opts = {
            'format': format_selector,
            'outtmpl': source_video_path,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'nocheckcertificate': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web']
                }
            }
        }

        if ffmpeg_exe:
            ydl_opts['ffmpeg_location'] = ffmpeg_exe

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                video_title = info.get('title', 'YouTube Video')
                duration = info.get('duration', 0)
        except Exception as dl_err:
            print(f"Initial yt-dlp download failed ({quality}), trying fallback format: {dl_err}")
            ydl_opts['format'] = 'best[ext=mp4]/best'
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                video_title = info.get('title', 'YouTube Video')
                duration = info.get('duration', 0)

        update_job(job_id, video_title=video_title, video_duration=duration, progress=25)

        # Check for very long videos (> 2 hours = 7200s)
        if duration > 7200:
            update_job(
                job_id,
                message="Warning: Video is longer than 2 hours. Clip processing might take extra time. Fast accuracy mode is recommended."
            )

        if not os.path.exists(source_video_path):
            files = [os.path.join(job_dir, f) for f in os.listdir(job_dir) if f.startswith("source")]
            if files:
                source_video_path = files[0]
            else:
                raise Exception("Failed to download video file from YouTube.")

        # STEP 2: Extract 16kHz WAV Audio & Transcribe with faster-whisper
        update_job(
            job_id,
            stage="transcribing",
            progress=25,
            message="Extracting audio track & initializing faster-whisper AI transcription..."
        )

        extracted = media_processor.extract_audio_wav(source_video_path, output_wav_path)
        if not extracted or not os.path.exists(output_wav_path):
            raise Exception("Failed to extract 16kHz mono audio track.")

        formatted_segments = transcribe_with_faster_whisper(
            job_id=job_id,
            audio_path=output_wav_path,
            video_id=video_id,
            accuracy_mode=accuracy_mode
        )

        # STEP 3: Multi-Signal Virality Analysis
        update_job(
            job_id,
            stage="analyzing",
            progress=60,
            message=f"Scoring virality (speech energy, hook keywords & pauses) for top {num_clips} clips..."
        )

        ranked_clips = analyzer.analyze_virality(
            audio_path=output_wav_path,
            transcript_segments=formatted_segments,
            video_duration=float(duration),
            target_clips=num_clips
        )

        if not ranked_clips:
            raise Exception("No valid clip candidates could be extracted.")

        # STEP 4: Cut Top N Clips (Original 16:9 + Vertical 9:16)
        total_clips = len(ranked_clips)
        update_job(
            job_id,
            stage="cutting",
            progress=65,
            message=f"Rendering {total_clips} viral clips at {quality_badge} (16:9 + 9:16 vertical crop)..."
        )

        final_clips = []
        for idx, clip in enumerate(ranked_clips):
            clip_id = f"clip_{idx + 1}"
            orig_filename = f"{clip_id}_orig.mp4"
            vert_filename = f"{clip_id}_vert.mp4"

            orig_path = os.path.join(job_dir, orig_filename)
            vert_path = os.path.join(job_dir, vert_filename)

            # Render original aspect ratio clip
            media_processor.cut_clip_original(
                video_path=source_video_path,
                output_clip_path=orig_path,
                start_sec=clip["start"],
                end_sec=clip["end"]
            )

            # Render 9:16 vertical crop clip
            media_processor.cut_clip_vertical(
                video_path=source_video_path,
                output_clip_path=vert_path,
                start_sec=clip["start"],
                end_sec=clip["end"]
            )

            clip_entry = {
                "id": clip_id,
                "rank": clip["rank"],
                "start": clip["start"],
                "end": clip["end"],
                "duration": clip["duration"],
                "score": clip["score"],
                "reason": clip["reason"],
                "quality": quality_badge,
                "text": clip["text"][:140] + ("..." if len(clip["text"]) > 140 else ""),
                "preview_url_original": f"/api/media/{job_id}/{orig_filename}",
                "preview_url_vertical": f"/api/media/{job_id}/{vert_filename}",
                "filename_original": orig_filename,
                "filename_vertical": vert_filename
            }
            final_clips.append(clip_entry)

            prog = 65 + int(((idx + 1) / total_clips) * 30)
            update_job(
                job_id,
                progress=prog,
                message=f"Rendered clip {idx + 1} of {total_clips} ({clip['reason']})..."
            )

        # STEP 5: Complete & Schedule Auto-Cleanup
        update_job(
            job_id,
            stage="completed",
            progress=100,
            message=f"Successfully generated {total_clips} viral clips!",
            clips=final_clips,
            eta_seconds=0
        )

        schedule_auto_cleanup(job_dir, delay_seconds=3600)

    except Exception as e:
        error_msg = str(e)
        print(f"Pipeline error for job {job_id}: {error_msg}")
        update_job(job_id, error=error_msg)
