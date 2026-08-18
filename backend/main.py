import os
import uuid
import threading
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, HttpUrl

from pipeline import JOBS, JOBS_LOCK, BASE_STORAGE_DIR, run_pipeline
import media_processor

app = FastAPI(
    title="SRI Clips API",
    description="AI-powered YouTube Viral Short Clip Generator API",
    version="1.0.0"
)

# Enable CORS for Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow local frontend development requests
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessRequest(BaseModel):
    url: str
    quality: str = "720p"  # "360p", "480p", "720p", "1080p", "best"
    num_clips: int = 10    # 3, 5, 10, 15, 20
    accuracy_mode: str = "balanced" # "fast", "balanced", "high_accuracy"


@app.get("/")
def root():
    return {"message": "SRI Clips API backend is running."}


@app.post("/api/process")
def process_url(req: ProcessRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="YouTube URL is required.")

    if not ("youtube.com" in url or "youtu.be" in url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL. Please provide a valid youtube.com or youtu.be link.")

    quality = req.quality if req.quality in ["360p", "480p", "720p", "1080p", "best"] else "720p"
    num_clips = max(1, min(20, req.num_clips))
    accuracy_mode = req.accuracy_mode if req.accuracy_mode in ["fast", "balanced", "high_accuracy"] else "balanced"

    job_id = f"job_{uuid.uuid4().hex[:10]}"

    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "url": url,
            "quality": quality,
            "num_clips": num_clips,
            "accuracy_mode": accuracy_mode,
            "stage": "queued",
            "progress": 0,
            "message": "Job queued for processing...",
            "video_title": "",
            "video_duration": 0,
            "eta_seconds": 0,
            "quality_badge": "",
            "clips": [],
            "error": None
        }

    # Start pipeline in background thread
    t = threading.Thread(
        target=run_pipeline,
        args=(job_id, url, quality, num_clips, accuracy_mode),
        daemon=True
    )
    t.start()

    return {"job_id": job_id, "status": "queued"}



@app.get("/api/status/{job_id}")
def get_status(job_id: str):
    with JOBS_LOCK:
        if job_id not in JOBS:
            raise HTTPException(status_code=404, detail="Job ID not found.")
        return JOBS[job_id]


@app.get("/api/media/{job_id}/{filename}")
def stream_media(job_id: str, filename: str):
    file_path = os.path.join(BASE_STORAGE_DIR, job_id, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Media file not found.")
    return FileResponse(file_path, media_type="video/mp4")


@app.get("/api/download/{job_id}/{clip_id}")
def download_clip(job_id: str, clip_id: str, format: str = Query("vertical", pattern="^(vertical|original)$")):
    job_dir = os.path.join(BASE_STORAGE_DIR, job_id)
    if not os.path.exists(job_dir):
        raise HTTPException(status_code=404, detail="Job not found or temporary files expired.")

    suffix = "vert.mp4" if format == "vertical" else "orig.mp4"
    filename = f"{clip_id}_{suffix}"
    file_path = os.path.join(job_dir, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Clip file not found.")

    download_name = f"SRI_Clip_{clip_id}_{format}.mp4"
    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename=download_name,
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'}
    )


@app.get("/api/download-all/{job_id}")
def download_all(job_id: str, format: str = Query("vertical", pattern="^(vertical|original|both)$")):
    job_dir = os.path.join(BASE_STORAGE_DIR, job_id)
    if not os.path.exists(job_dir):
        raise HTTPException(status_code=404, detail="Job not found or expired.")

    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job or job.get("stage") != "completed":
            raise HTTPException(status_code=400, detail="Clips processing not completed yet.")
        clips = job.get("clips", [])

    if not clips:
        raise HTTPException(status_code=404, detail="No clips available to zip.")

    file_map = {}
    for c in clips:
        clip_id = c["id"]
        rank = c["rank"]
        if format in ["vertical", "both"]:
            v_name = c["filename_vertical"]
            v_path = os.path.join(job_dir, v_name)
            file_map[f"Clip_{rank}_Vertical_9x16.mp4"] = v_path
        if format in ["original", "both"]:
            o_name = c["filename_original"]
            o_path = os.path.join(job_dir, o_name)
            file_map[f"Clip_{rank}_Original_16x9.mp4"] = o_path

    zip_filename = f"SRI_Clips_{job_id}_{format}.zip"
    zip_path = os.path.join(job_dir, zip_filename)

    success = media_processor.create_zip_archive(file_map, zip_path)
    if not success or not os.path.exists(zip_path):
        raise HTTPException(status_code=500, detail="Failed to generate zip archive.")

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=zip_filename,
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
    )
