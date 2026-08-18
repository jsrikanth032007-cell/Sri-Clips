# SRI Clips 🎬⚡

**SRI Clips** is an AI-powered full-stack web application that converts long YouTube videos into short, viral-style clips (15–60s) ready for TikTok, YouTube Shorts, and Instagram Reels.

---

## 🌟 Key Features

1. **YouTube Downloader**: Downloads best quality video (up to 1080p) automatically using `yt-dlp`.
2. **AI Speech Transcription**: Extracts 16kHz WAV audio and runs OpenAI Whisper AI to generate precise, timestamped transcripts.
3. **Multi-Signal Virality Scoring Engine**:
   - 🔊 **Audio Volume & Speech Energy Spikes**: Detects excitement, laughter, shouting, and high-energy reactions using RMS audio analysis.
   - 🎯 **Hook Keyword & NLP Analysis**: Detects retention hooks ("you won't believe", "here's why", "the secret is", questions, cliffhangers).
   - 🎭 **Sentiment & Emotion Peaks**: Scores intensity based on high-emotion vocabulary and punctuation density.
   - 🤫 **Pre-Segment Pause Detection**: Flags silence setups right before a reveal or punchline.
4. **Top 10 Candidate Selection**: Filters and ranks non-overlapping candidate segments.
5. **Ffmpeg Clip Cutting**:
   - **16:9 Original** format clips.
   - **9:16 Vertical Short** cropped clips (1080x1920 center crop).
6. **Results Dashboard**:
   - Inline video preview player.
   - Start / end timestamp and length indicator.
   - Auto-generated Virality Reason badge (e.g., *"High Speech Energy + Hook Keyword Setup"*).
   - Individual clip download button.
   - **Download All (.zip)** one-click archive button.
7. **Automated Temp File Cleanup**: Auto-deletes temp job folders after 1 hour.

---

## 🛠️ Tech Stack

- **Frontend**: Next.js (React 19), Tailwind CSS, Lucide Icons, Axios
- **Backend**: Python FastAPI, Uvicorn, background threads
- **Video & Audio Processing**: `yt-dlp`, `openai-whisper`, `scipy`, `numpy`, `imageio-ffmpeg`

---

## 🚀 How to Run locally

### Single Start Command

Run the following command from the root directory:

```bash
python run_app.py
```

or using npm:

```bash
npm start
```

This will launch both:
- **FastAPI Backend**: `http://127.0.0.1:8000`
- **Next.js Frontend**: `http://localhost:3000`

Open `http://localhost:3000` in your web browser to use SRI Clips!
