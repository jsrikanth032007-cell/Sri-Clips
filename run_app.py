import os
import sys
import subprocess
import time
import signal
import shutil

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
BIN_DIR = os.path.join(ROOT_DIR, "bin")
VENV_PYTHON = os.path.join(ROOT_DIR, "venv", "Scripts", "python.exe")

if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable


def setup_environment():
    """Ensures bin/ffmpeg.exe exists and is in PATH for all child processes."""
    os.makedirs(BIN_DIR, exist_ok=True)
    ffmpeg_exe = os.path.join(BIN_DIR, "ffmpeg.exe")
    
    if not os.path.exists(ffmpeg_exe):
        try:
            import imageio_ffmpeg
            src = imageio_ffmpeg.get_ffmpeg_exe()
            if src and os.path.exists(src):
                shutil.copy2(src, ffmpeg_exe)
                print(f"Set up ffmpeg binary in: {ffmpeg_exe}")
        except Exception as e:
            print(f"Warning: Could not auto-copy ffmpeg: {e}")

    os.environ["PATH"] = BIN_DIR + os.pathsep + os.environ.get("PATH", "")


def main():
    setup_environment()

    print("=" * 60)
    print("   STARTING SRI CLIPS (Backend + Frontend)")
    print("=" * 60)
    print(f"Using Python executable: {VENV_PYTHON}")

    # Start FastAPI Backend
    print("\n[1/2] Starting FastAPI Backend on http://127.0.0.1:8000...")
    backend_cmd = [
        VENV_PYTHON, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"
    ]
    backend_process = subprocess.Popen(backend_cmd, cwd=BACKEND_DIR, env=os.environ.copy())

    # Start Next.js Frontend
    print("[2/2] Starting Next.js Frontend on http://localhost:3000...")
    frontend_cmd = "npm run dev"
    frontend_process = subprocess.Popen(frontend_cmd, cwd=FRONTEND_DIR, shell=True, env=os.environ.copy())

    print("\n" + "=" * 60)
    print("   SRI CLIPS IS NOW RUNNING!")
    print("   Open UI in Browser: http://localhost:3000")
    print("   API Docs: http://127.0.0.1:8000/docs")
    print("=" * 60 + "\n")

    def signal_handler(sig, frame):
        print("\nStopping SRI Clips services...")
        backend_process.terminate()
        frontend_process.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        while True:
            time.sleep(1)
            if backend_process.poll() is not None:
                print("Backend process stopped.")
                break
            if frontend_process.poll() is not None:
                print("Frontend process stopped.")
                break
    except KeyboardInterrupt:
        pass
    finally:
        backend_process.terminate()
        frontend_process.terminate()


if __name__ == "__main__":
    main()
