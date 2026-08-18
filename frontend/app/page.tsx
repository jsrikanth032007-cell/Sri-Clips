'use client';

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  Scissors,
  Sparkles,
  Download,
  FileArchive,
  AlertCircle,
  CheckCircle2,
  Clock,
  Zap,
  Film,
  Layers,
  ArrowRight,
  Clipboard,
  Sliders,
  Settings,
  Gauge
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || '';

interface Clip {
  id: string;
  rank: number;
  start: number;
  end: number;
  duration: number;
  score: number;
  reason: string;
  quality?: string;
  text: string;
  preview_url_original: string;
  preview_url_vertical: string;
  filename_original: string;
  filename_vertical: string;
}

interface JobStatus {
  id: string;
  url: string;
  quality?: string;
  num_clips?: number;
  accuracy_mode?: string;
  stage: 'queued' | 'downloading' | 'transcribing' | 'analyzing' | 'cutting' | 'completed' | 'error';
  progress: number;
  message: string;
  video_title?: string;
  video_duration?: number;
  eta_seconds?: number;
  quality_badge?: string;
  clips: Clip[];
  error?: string;
}

export default function HomePage() {
  const [url, setUrl] = useState('');
  const [quality, setQuality] = useState<'360p' | '480p' | '720p' | '1080p' | 'best'>('720p');
  const [numClips, setNumClips] = useState<number>(10);
  const [accuracyMode, setAccuracyMode] = useState<'fast' | 'balanced' | 'high_accuracy'>('balanced');
  
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobData, setJobData] = useState<JobStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cropFormat, setCropFormat] = useState<'vertical' | 'original'>('vertical');
  const [downloadingZip, setDownloadingZip] = useState(false);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Poll job status
  useEffect(() => {
    if (!jobId) return;

    const checkStatus = async () => {
      try {
        const res = await axios.get<JobStatus>(`${API_BASE}/api/status/${jobId}`);
        const data = res.data;
        setJobData(data);

        if (data.stage === 'completed' || data.stage === 'error') {
          setLoading(false);
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
          if (data.stage === 'error') {
            setError(data.error || 'An error occurred while processing the video.');
          }
        }
      } catch (err: any) {
        console.error('Failed to poll status:', err);
      }
    };

    checkStatus();
    pollIntervalRef.current = setInterval(checkStatus, 1200);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [jobId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setError(null);
    setJobData(null);
    setLoading(true);

    try {
      const res = await axios.post<{ job_id: string; status: string }>(`${API_BASE}/api/process`, {
        url: url.trim(),
        quality,
        num_clips: numClips,
        accuracy_mode: accuracyMode,
      });
      setJobId(res.data.job_id);
    } catch (err: any) {
      setLoading(false);
      const msg = err.response?.data?.detail || 'Failed to submit YouTube video. Check URL and backend server connection.';
      setError(msg);
    }
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) setUrl(text);
    } catch (e) {
      console.warn('Clipboard access not allowed');
    }
  };

  const handleDownloadSingle = (clipId: string) => {
    if (!jobId) return;
    const downloadUrl = `${API_BASE}/api/download/${jobId}/${clipId}?format=${cropFormat}`;
    window.open(downloadUrl, '_blank');
  };

  const handleDownloadAll = async () => {
    if (!jobId) return;
    setDownloadingZip(true);
    try {
      const downloadUrl = `${API_BASE}/api/download-all/${jobId}?format=${cropFormat}`;
      window.open(downloadUrl, '_blank');
    } finally {
      setTimeout(() => setDownloadingZip(false), 2000);
    }
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const isStepActive = (stepStage: string) => {
    if (!jobData) return false;
    const stages = ['queued', 'downloading', 'transcribing', 'analyzing', 'cutting', 'completed'];
    const currentIdx = stages.indexOf(jobData.stage);
    const stepIdx = stages.indexOf(stepStage);
    return currentIdx >= stepIdx;
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#090d16] text-gray-100 selection:bg-purple-500 selection:text-white">
      {/* HEADER */}
      <header className="border-b border-gray-800/80 bg-[#0d121f]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-purple-600 to-pink-500 p-0.5 flex items-center justify-center shadow-lg shadow-purple-500/20">
              <div className="w-full h-full bg-[#0d121f] rounded-[10px] flex items-center justify-center">
                <Scissors className="w-5 h-5 text-purple-400" />
              </div>
            </div>
            <div>
              <span className="font-extrabold text-xl tracking-tight text-white flex items-center gap-2">
                SRI CLIPS <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 font-semibold">faster-whisper AI</span>
              </span>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-400">
            <span className="hidden sm:flex items-center gap-1.5 bg-gray-800/50 px-3 py-1 rounded-full border border-gray-700/50 text-xs">
              <Zap className="w-3.5 h-3.5 text-amber-400" /> 4x Faster AI Engine
            </span>
          </div>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
        {/* HERO SECTION */}
        <section className="text-center max-w-3xl mx-auto space-y-4 pt-2">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs sm:text-sm font-medium">
            <Sparkles className="w-4 h-4 text-purple-400 animate-pulse" /> Turn Long Videos into Short Viral Clips
          </div>
          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
            Extract <span className="gradient-text">Viral Moments</span> automatically.
          </h1>
          <p className="text-gray-400 text-base sm:text-lg max-w-2xl mx-auto">
            Paste any YouTube link. Our AI analyzes speech energy spikes, hook phrases, emotional intensity & tension pauses to cut top short clips ready for TikTok, Shorts & Reels.
          </p>
        </section>

        {/* INPUT FORM CARD */}
        <section className="max-w-3xl mx-auto">
          <div className="glass-panel p-5 sm:p-7 rounded-2xl shadow-2xl space-y-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* URL INPUT */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-gray-300 uppercase tracking-wider flex items-center justify-between">
                  <span>YouTube Video Link</span>
                  <span className="text-gray-500 text-[11px] font-normal">Supports up to 2hr videos</span>
                </label>
                <div className="relative flex items-center">
                  <div className="absolute left-4 text-red-500">
                    <svg className="w-6 h-6 fill-current text-red-500" viewBox="0 0 24 24">
                      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                    </svg>
                  </div>
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="Paste YouTube Video URL (e.g. https://www.youtube.com/watch?v=...)"
                    className="w-full bg-[#131b2e] border border-gray-700/70 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 rounded-xl pl-12 pr-24 py-3.5 text-gray-100 placeholder-gray-500 text-sm sm:text-base outline-none transition-all"
                    disabled={loading}
                    required
                  />
                  <button
                    type="button"
                    onClick={handlePaste}
                    className="absolute right-3 px-3 py-1.5 text-xs text-gray-400 hover:text-white bg-gray-800/80 hover:bg-gray-700/80 rounded-lg flex items-center gap-1.5 border border-gray-700 transition"
                    title="Paste from Clipboard"
                  >
                    <Clipboard className="w-3.5 h-3.5" /> Paste
                  </button>
                </div>
              </div>

              {/* OPTIONS GRID */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
                {/* QUALITY SELECTOR */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
                    <Settings className="w-3.5 h-3.5 text-purple-400" /> Download Quality
                  </label>
                  <select
                    value={quality}
                    onChange={(e) => setQuality(e.target.value as any)}
                    disabled={loading}
                    className="w-full bg-[#131b2e] border border-gray-700/70 focus:border-purple-500 rounded-xl px-3 py-2.5 text-xs sm:text-sm text-gray-200 outline-none cursor-pointer"
                  >
                    <option value="360p">360p (Fastest)</option>
                    <option value="480p">480p (Fast)</option>
                    <option value="720p">720p HD (Default)</option>
                    <option value="1080p">1080p FHD</option>
                    <option value="best">Best Available</option>
                  </select>
                </div>

                {/* NUMBER OF CLIPS SELECTOR */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5 justify-between">
                    <span className="flex items-center gap-1.5">
                      <Sliders className="w-3.5 h-3.5 text-blue-400" /> Number of Clips
                    </span>
                    <span className="text-purple-400 font-bold text-xs">{numClips} Clips</span>
                  </label>
                  <select
                    value={numClips}
                    onChange={(e) => setNumClips(Number(e.target.value))}
                    disabled={loading}
                    className="w-full bg-[#131b2e] border border-gray-700/70 focus:border-purple-500 rounded-xl px-3 py-2.5 text-xs sm:text-sm text-gray-200 outline-none cursor-pointer"
                  >
                    <option value={3}>3 Clips (Quick)</option>
                    <option value={5}>5 Clips</option>
                    <option value={10}>10 Clips (Default)</option>
                    <option value={15}>15 Clips</option>
                    <option value={20}>20 Clips (Max)</option>
                  </select>
                </div>

                {/* ACCURACY VS SPEED TOGGLE */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
                    <Gauge className="w-3.5 h-3.5 text-emerald-400" /> Accuracy vs Speed
                  </label>
                  <div className="bg-[#131b2e] border border-gray-700/70 rounded-xl p-1 flex items-center h-[42px]">
                    <button
                      type="button"
                      onClick={() => setAccuracyMode('fast')}
                      disabled={loading}
                      className={`flex-1 py-1 text-[11px] font-semibold rounded-lg transition ${
                        accuracyMode === 'fast'
                          ? 'bg-purple-600 text-white shadow'
                          : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      Fast
                    </button>
                    <button
                      type="button"
                      onClick={() => setAccuracyMode('balanced')}
                      disabled={loading}
                      className={`flex-1 py-1 text-[11px] font-semibold rounded-lg transition ${
                        accuracyMode === 'balanced'
                          ? 'bg-purple-600 text-white shadow'
                          : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      Balanced
                    </button>
                    <button
                      type="button"
                      onClick={() => setAccuracyMode('high_accuracy')}
                      disabled={loading}
                      className={`flex-1 py-1 text-[11px] font-semibold rounded-lg transition ${
                        accuracyMode === 'high_accuracy'
                          ? 'bg-purple-600 text-white shadow'
                          : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      High
                    </button>
                  </div>
                </div>
              </div>

              {/* SUBMIT BUTTON */}
              <button
                type="submit"
                disabled={loading || !url.trim()}
                className="w-full gradient-btn py-4 px-6 rounded-xl font-bold text-white text-base flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Processing Video...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5 text-amber-300" />
                    <span>Generate {numClips} Viral Clips</span>
                    <ArrowRight className="w-5 h-5 ml-1" />
                  </>
                )}
              </button>
            </form>

            {/* DEMO SAMPLE LINKS */}
            <div className="pt-2 border-t border-gray-800/60 flex items-center justify-between text-xs text-gray-400">
              <span className="text-gray-500">Quick Test Links:</span>
              <div className="flex items-center gap-2 overflow-x-auto py-1">
                <button
                  onClick={() => setUrl('https://www.youtube.com/watch?v=dQw4w9WgXcQ')}
                  className="px-2.5 py-1 rounded-md bg-gray-800/50 hover:bg-gray-700/50 text-gray-300 transition"
                >
                  Rickroll Sample
                </button>
                <button
                  onClick={() => setUrl('https://www.youtube.com/watch?v=jNQXAC9IVRw')}
                  className="px-2.5 py-1 rounded-md bg-gray-800/50 hover:bg-gray-700/50 text-gray-300 transition"
                >
                  Me at the zoo
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* ERROR DISPLAY */}
        {error && (
          <section className="max-w-3xl mx-auto">
            <div className="bg-red-500/10 border border-red-500/30 p-4 rounded-xl flex items-start gap-3 text-red-300">
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div className="flex-1 text-sm">
                <p className="font-semibold text-red-200">Processing Error</p>
                <p className="mt-0.5 opacity-90">{error}</p>
              </div>
              <button
                onClick={() => setError(null)}
                className="text-xs px-2.5 py-1 bg-red-500/20 hover:bg-red-500/30 rounded-md transition"
              >
                Dismiss
              </button>
            </div>
          </section>
        )}

        {/* PROCESSING PROGRESS CARD */}
        {jobData && jobData.stage !== 'completed' && jobData.stage !== 'error' && (
          <section className="max-w-3xl mx-auto">
            <div className="glass-panel p-6 rounded-2xl space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-lg text-white flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-purple-500 animate-ping" />
                    Processing Video Clips
                  </h3>
                  {jobData.video_title && (
                    <p className="text-sm text-purple-300 mt-1 line-clamp-1 font-medium">
                      "{jobData.video_title}"
                    </p>
                  )}
                </div>
                <div className="text-right">
                  <span className="text-2xl font-extrabold text-purple-400">
                    {jobData.progress}%
                  </span>
                  {jobData.eta_seconds !== undefined && jobData.eta_seconds > 0 && (
                    <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1 justify-end">
                      <Clock className="w-3 h-3 text-amber-400" /> ETA ~{jobData.eta_seconds}s
                    </p>
                  )}
                </div>
              </div>

              {/* PROGRESS BAR */}
              <div className="w-full bg-gray-800/80 rounded-full h-3 overflow-hidden p-0.5 border border-gray-700/50">
                <div
                  className="bg-gradient-to-r from-purple-600 via-blue-500 to-emerald-400 h-full rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${jobData.progress}%` }}
                />
              </div>

              <p className="text-sm text-gray-300 italic text-center font-mono bg-gray-900/60 py-2 px-3 rounded-lg border border-gray-800">
                "{jobData.message}"
              </p>

              {/* PIPELINE STEPS */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                {[
                  { key: 'downloading', label: '1. Download', desc: `yt-dlp ${jobData.quality_badge || quality}` },
                  { key: 'transcribing', label: '2. Transcribe', desc: 'faster-whisper' },
                  { key: 'analyzing', label: '3. AI Score', desc: 'Energy & Hooks' },
                  { key: 'cutting', label: '4. Render Clips', desc: `Cut ${numClips} Clips` },
                ].map((step) => {
                  const active = isStepActive(step.key);
                  const isCurrent = jobData.stage === step.key;
                  return (
                    <div
                      key={step.key}
                      className={`p-3 rounded-xl border text-center transition-all ${
                        isCurrent
                          ? 'bg-purple-500/20 border-purple-500/50 text-white shadow-lg shadow-purple-500/10'
                          : active
                          ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                          : 'bg-gray-900/40 border-gray-800 text-gray-500'
                      }`}
                    >
                      <div className="flex justify-center mb-1">
                        {active && !isCurrent ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        ) : isCurrent ? (
                          <div className="w-4 h-4 rounded-full border-2 border-purple-400 border-t-transparent animate-spin" />
                        ) : (
                          <div className="w-4 h-4 rounded-full border border-gray-600" />
                        )}
                      </div>
                      <p className="font-semibold text-xs">{step.label}</p>
                      <p className="text-[10px] opacity-70 mt-0.5">{step.desc}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>
        )}

        {/* RESULTS GRID SECTION */}
        {jobData?.stage === 'completed' && jobData.clips.length > 0 && (
          <section className="space-y-6">
            {/* RESULTS TOOLBAR */}
            <div className="glass-panel p-5 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                  <Sparkles className="w-6 h-6 text-amber-400" /> Top {jobData.clips.length} Viral Clips
                </h2>
                {jobData.video_title && (
                  <p className="text-sm text-gray-400 mt-0.5 line-clamp-1">
                    Source: <span className="text-gray-200">{jobData.video_title}</span>
                  </p>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-3 w-full md:w-auto justify-end">
                {/* FORMAT TOGGLE */}
                <div className="bg-[#121929] border border-gray-700/70 rounded-xl p-1 flex items-center">
                  <button
                    onClick={() => setCropFormat('vertical')}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition ${
                      cropFormat === 'vertical'
                        ? 'bg-purple-600 text-white shadow-md'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    <Layers className="w-3.5 h-3.5" /> 9:16 Vertical Short
                  </button>
                  <button
                    onClick={() => setCropFormat('original')}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition ${
                      cropFormat === 'original'
                        ? 'bg-purple-600 text-white shadow-md'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    <Film className="w-3.5 h-3.5" /> 16:9 Original
                  </button>
                </div>

                {/* DOWNLOAD ALL ZIP */}
                <button
                  onClick={handleDownloadAll}
                  disabled={downloadingZip}
                  className="gradient-btn py-2.5 px-4 rounded-xl font-bold text-xs sm:text-sm text-white flex items-center gap-2 cursor-pointer"
                >
                  <FileArchive className="w-4 h-4 text-emerald-300" />
                  <span>{downloadingZip ? 'Preparing Zip...' : 'Download All (.zip)'}</span>
                </button>
              </div>
            </div>

            {/* CLIPS GRID */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {jobData.clips.map((clip) => {
                const previewSrc =
                  cropFormat === 'vertical'
                    ? `${API_BASE}${clip.preview_url_vertical}`
                    : `${API_BASE}${clip.preview_url_original}`;

                const badge = clip.quality || jobData.quality_badge || '720p HD';

                return (
                  <div
                    key={clip.id}
                    className="glass-panel glass-panel-hover rounded-2xl overflow-hidden flex flex-col justify-between border border-gray-800"
                  >
                    {/* CARD HEADER */}
                    <div className="p-4 bg-gray-900/60 border-b border-gray-800/80 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="w-7 h-7 rounded-lg bg-purple-500/20 border border-purple-500/30 text-purple-300 font-extrabold text-xs flex items-center justify-center">
                          #{clip.rank}
                        </span>
                        <span className="bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1">
                          <Zap className="w-3 h-3 fill-amber-400" /> {clip.score} Score
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded-md border border-blue-500/30 font-mono">
                          {badge}
                        </span>
                        <span className="text-xs font-medium text-gray-400 flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5" /> {formatSeconds(clip.start)} - {formatSeconds(clip.end)}
                        </span>
                      </div>
                    </div>

                    {/* VIDEO PLAYER PREVIEW */}
                    <div className="relative bg-black flex items-center justify-center overflow-hidden min-h-[240px]">
                      <video
                        key={previewSrc}
                        src={previewSrc}
                        controls
                        preload="metadata"
                        className={`w-full ${cropFormat === 'vertical' ? 'max-h-[360px] object-contain' : 'aspect-video object-cover'}`}
                      />
                    </div>

                    {/* VIRALITY REASON & TRANSCRIPT */}
                    <div className="p-4 space-y-3 flex-1 flex flex-col justify-between">
                      <div className="space-y-2">
                        {/* REASON BADGE */}
                        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs font-semibold">
                          <Sparkles className="w-3 h-3 text-purple-400" />
                          <span>{clip.reason}</span>
                        </div>

                        {/* TRANSCRIPT TEXT */}
                        <p className="text-xs text-gray-300 line-clamp-3 italic bg-gray-900/40 p-2.5 rounded-lg border border-gray-800/60">
                          "{clip.text}"
                        </p>
                      </div>

                      {/* DOWNLOAD BUTTON */}
                      <button
                        onClick={() => handleDownloadSingle(clip.id)}
                        className="w-full mt-2 py-2.5 px-4 bg-purple-600/30 hover:bg-purple-600/50 border border-purple-500/40 rounded-xl text-xs font-bold text-purple-200 flex items-center justify-center gap-2 transition"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Download Clip ({cropFormat === 'vertical' ? '9:16' : '16:9'})</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </main>

      {/* FOOTER */}
      <footer className="border-t border-gray-800/60 py-6 text-center text-xs text-gray-500">
        <p>SRI CLIPS • YouTube Viral Short Clip Generator • Powered by faster-whisper & FastAPI</p>
      </footer>
    </div>
  );
}
