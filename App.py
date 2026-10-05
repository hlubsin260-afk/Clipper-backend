import os
import subprocess
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid

app = FastAPI(title="AI Clipper Cloud Backend")

DOWNLOAD_DIR = "clips"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class ClipRequest(BaseModel):
    url: str
    start_time: str # Format "00:01:20"
    end_time: str   # Format "00:02:10"

def process_video_clip(url: str, start: str, end: str, output_path: str):
    """
    Mendownload video menggunakan yt-dlp dan memotong secara langsung 
    menggunakan FFmpeg tanpa mendownload seluruh video utuh.
    """
    # Menggunakan yt-dlp untuk stream dan memotong langsung via FFmpeg
    cmd = [
        "yt-dlp",
        "-g", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        url
    ]
    try:
        # Ambil direct URL video
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        stream_urls = result.stdout.strip().split('\n')
        
        video_url = stream_urls[0]
        audio_url = stream_urls[1] if len(stream_urls) > 1 else video_url

        # Potong langsung dan ubah rasio jadi 9:16 (vertikal Shorts)
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-ss", start,
            "-i", video_url,
            "-ss", start,
            "-i", audio_url,
            "-to", end,
            "-vf", "crop=ih*(9/16):ih", # Crop ke format 9:16 vertikal
            "-c:v", "libx264",
            "-c:a", "aac",
            output_path
        ]
        subprocess.run(ffmpeg_cmd, check=True)
    except Exception as e:
        print(f"Error processing video: {e}")

@app.post("/api/cut-clip")
def cut_clip(req: ClipRequest, background_tasks: BackgroundTasks):
    filename = f"clip_{uuid.uuid4().hex[:8]}.mp4"
    output_path = os.path.join(DOWNLOAD_DIR, filename)
    
    # Jalankan proses pemotongan video di background
    process_video_clip(req.url, req.start_time, req.end_time, output_path)
    
    if os.path.exists(output_path):
        return {"status": "success", "download_url": f"/api/download/{filename}"}
    else:
        raise HTTPException(status_code=500, detail="Gagal memproses potongan video")

@app.get("/api/download/{filename}")
def download_clip(filename: str):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="video/mp4", filename=filename)
    raise HTTPException(status_code=404, detail="File tidak ditemukan")
