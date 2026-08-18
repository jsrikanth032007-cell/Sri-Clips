import os
import shutil
import subprocess
import zipfile
import imageio_ffmpeg

def ensure_ffmpeg_in_path() -> str:
    """Ensures ffmpeg.exe exists in bin/ and prepends bin/ to os.environ['PATH']."""
    bin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin"))
    os.makedirs(bin_dir, exist_ok=True)
    ffmpeg_exe = os.path.join(bin_dir, "ffmpeg.exe")

    if not os.path.exists(ffmpeg_exe):
        try:
            src = imageio_ffmpeg.get_ffmpeg_exe()
            if src and os.path.exists(src):
                shutil.copy2(src, ffmpeg_exe)
        except Exception as e:
            print(f"Error setting up ffmpeg binary in bin/: {e}")

    if bin_dir not in os.environ["PATH"]:
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]

    return ffmpeg_exe if os.path.exists(ffmpeg_exe) else "ffmpeg"


def get_ffmpeg_path() -> str:
    return ensure_ffmpeg_in_path()


def extract_audio_wav(video_path: str, output_wav_path: str) -> bool:
    """Extracts 16kHz mono WAV audio from video file."""
    ffmpeg = get_ffmpeg_path()
    cmd = [
        ffmpeg,
        "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_wav_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return os.path.exists(output_wav_path)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg audio extraction error: {e.stderr.decode('utf-8', errors='ignore')}")
        return False


def cut_clip_original(video_path: str, output_clip_path: str, start_sec: float, end_sec: float) -> bool:
    """Cuts a clip in original aspect ratio (16:9 / source format)."""
    ffmpeg = get_ffmpeg_path()
    duration = end_sec - start_sec
    cmd = [
        ffmpeg,
        "-y",
        "-ss", str(start_sec),
        "-i", video_path,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        "-avoid_negative_ts", "make_zero",
        output_clip_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return os.path.exists(output_clip_path)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg original clip cut error: {e.stderr.decode('utf-8', errors='ignore')}")
        return False


def cut_clip_vertical(video_path: str, output_clip_path: str, start_sec: float, end_sec: float) -> bool:
    """
    Cuts a clip formatted in 9:16 vertical ratio (Shorts/TikTok style).
    Uses center-crop filter for crisp 1080x1920 output.
    """
    ffmpeg = get_ffmpeg_path()
    duration = end_sec - start_sec
    filter_complex = "crop=ih*9/16:ih:(iw-ow)/2:0,scale=1080:1920:flags=bicubic"

    cmd = [
        ffmpeg,
        "-y",
        "-ss", str(start_sec),
        "-i", video_path,
        "-t", str(duration),
        "-vf", filter_complex,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        "-avoid_negative_ts", "make_zero",
        output_clip_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return os.path.exists(output_clip_path)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg vertical clip cut error: {e.stderr.decode('utf-8', errors='ignore')}")
        fallback_cmd = [
            ffmpeg, "-y", "-ss", str(start_sec), "-i", video_path, "-t", str(duration),
            "-vf", "crop=ih*9/16:ih", "-c:v", "libx264", "-c:a", "aac", output_clip_path
        ]
        try:
            subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return os.path.exists(output_clip_path)
        except Exception:
            return False


def create_zip_archive(file_map: dict, output_zip_path: str) -> bool:
    """Creates a zip archive from a dictionary of {zip_internal_filename: local_filepath}."""
    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for zip_name, file_path in file_map.items():
                if os.path.exists(file_path):
                    zf.write(file_path, arcname=zip_name)
        return os.path.exists(output_zip_path)
    except Exception as e:
        print(f"Error creating zip archive: {e}")
        return False
