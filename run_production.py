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
    """Ensures ffmpeg is in PATH for all child processes."""
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

    port = os.environ.get("PORT", "3000")

    print("=" * 60)
    print("   STARTING SRI CLIPS (PRODUCTION MODE)")
    print(f"   Python Executable: {VENV_PYTHON}")
    print(f"   Public Port: {port}")
    print("=" * 60)

    # Step 1: Check if Next.js build folder exists, only build if missing
    next_build_dir = os.path.join(FRONTEND_DIR, ".next")
    if not os.path.exists(next_build_dir):
        print("\n[1/3] Building Next.js production bundle...")
        build_proc = subprocess.run("npx next build", cwd=FRONTEND_DIR, shell=True)
        if build_proc.returncode != 0:
            print("Warning: Next.js build returned non-zero code.")
    else:
        print("\n[1/3] Pre-built Next.js bundle found (.next). Skipping runtime build...")

    # Step 2: Start FastAPI Production Server on 0.0.0.0:8000
    print("\n[2/3] Starting FastAPI Backend on http://0.0.0.0:8000...")
    backend_cmd = [
        VENV_PYTHON, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"
    ]
    backend_process = subprocess.Popen(backend_cmd, cwd=BACKEND_DIR, env=os.environ.copy())

    # Wait for Uvicorn backend to bind port 8000
    time.sleep(2.0)

    # Step 3: Start Next.js Production Server on public $PORT
    print(f"\n[3/3] Starting Next.js Production Server on port {port}...")
    frontend_cmd = f"npx next start -p {port}"
    frontend_process = subprocess.Popen(frontend_cmd, cwd=FRONTEND_DIR, shell=True, env=os.environ.copy())

    print("\n" + "=" * 60)
    print("   SRI CLIPS IS LIVE!")
    print(f"   Public Web App: http://0.0.0.0:{port}")
    print("   FastAPI Internal: http://127.0.0.1:8000")
    print("=" * 60 + "\n")

    def signal_handler(sig, frame):
        print("\nStopping Sri Clips production services...")
        backend_process.terminate()
        frontend_process.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        while True:
            time.sleep(1)
            if backend_process.poll() is not None:
                print(f"WARNING: Backend process exited with code {backend_process.poll()}!")
                # Restart backend if it crashed unexpectedly
                print("Attempting to restart FastAPI Backend...")
                backend_process = subprocess.Popen(backend_cmd, cwd=BACKEND_DIR, env=os.environ.copy())
                time.sleep(2.0)

            if frontend_process.poll() is not None:
                print(f"WARNING: Frontend process exited with code {frontend_process.poll()}!")
                print("Attempting to restart Next.js Frontend...")
                frontend_process = subprocess.Popen(frontend_cmd, cwd=FRONTEND_DIR, shell=True, env=os.environ.copy())
                time.sleep(2.0)

    except KeyboardInterrupt:
        pass
    finally:
        backend_process.terminate()
        frontend_process.terminate()


if __name__ == "__main__":
    main()
