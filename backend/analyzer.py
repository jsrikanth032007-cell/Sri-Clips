import math
import re
import numpy as np
from scipy.io import wavfile

# List of viral hook phrases & patterns
HOOK_PATTERNS = [
    r"you won'?t believe",
    r"the secret is",
    r"here'?s why",
    r"stop doing",
    r"how to",
    r"the truth about",
    r"nobody (talks|knows) about",
    r"the biggest mistake",
    r"never do this",
    r"the best way",
    r"mind blowing",
    r"unbelievable",
    r"insane",
    r"secret tip",
    r"what happens when",
    r"listen to this",
    r"i couldn'?t believe",
    r"this changes everything",
    r"the real reason",
    r"number one",
    r"top \d+",
]

EMOTION_KEYWORDS = {
    "shock", "insane", "crazy", "omg", "wow", "hilarious", "died", "crying",
    "laughing", "secret", "worst", "best", "amazing", "terrible", "wrong",
    "genius", "scam", "huge", "fatal", "never", "always", "guaranteed"
}


def compute_audio_energy(audio_path: str):
    """
    Computes RMS audio energy per 1.0 second window.
    Returns:
        sample_rate (int)
        energy_per_sec (dict of second_index -> normalized_energy)
    """
    try:
        sample_rate, data = wavfile.read(audio_path)
        if data.ndim > 1:
            data = data.mean(axis=1) # Convert to mono
            
        data = data.astype(np.float32)
        samples_per_sec = sample_rate
        total_secs = int(len(data) / samples_per_sec)
        
        energy_per_sec = {}
        for s in range(total_secs):
            chunk = data[s * samples_per_sec : (s + 1) * samples_per_sec]
            if len(chunk) > 0:
                rms = np.sqrt(np.mean(chunk**2))
                energy_per_sec[s] = rms
            else:
                energy_per_sec[s] = 0.0

        # Normalize energy values to 0.0 - 1.0
        max_e = max(energy_per_sec.values()) if energy_per_sec else 1.0
        if max_e > 0:
            for s in energy_per_sec:
                energy_per_sec[s] = float(energy_per_sec[s] / max_e)

        return sample_rate, energy_per_sec
    except Exception as e:
        print(f"Error computing audio energy: {e}")
        return 16000, {}


def evaluate_text_hook(text: str) -> float:
    """Evaluates hook score based on pattern matches, questions, and exclamations."""
    text_lower = text.lower()
    score = 0.0

    for pattern in HOOK_PATTERNS:
        if re.search(pattern, text_lower):
            score += 2.5

    if "?" in text:
        score += 1.5
    if "!" in text:
        score += 1.0

    return min(10.0, score)


def evaluate_sentiment(text: str) -> float:
    """Evaluates sentiment & emotional intensity based on keyword density."""
    words = re.findall(r'\w+', text.lower())
    if not words:
        return 0.0

    emotion_count = sum(1 for w in words if w in EMOTION_KEYWORDS)
    caps_count = sum(1 for w in re.findall(r'\b[A-Z]{2,}\b', text))

    score = (emotion_count * 1.8) + (caps_count * 1.0)
    return min(10.0, score)


def evaluate_pre_pause(start_sec: float, energy_map: dict) -> float:
    """
    Measures silence/pause in the 1.5 seconds immediately preceding segment start.
    Preceding silence indicates setup/cliffhanger/tension before a reveal.
    """
    sec = int(start_sec)
    window = [sec - 2, sec - 1]
    pre_energy = [energy_map.get(s, 0.5) for s in window if s >= 0]
    
    if not pre_energy:
        return 0.0

    avg_pre_energy = sum(pre_energy) / len(pre_energy)
    # Lower energy right before means higher pause score
    pause_score = max(0.0, (0.4 - avg_pre_energy) * 5.0)
    return min(10.0, pause_score)


def generate_virality_reason(energy_score: float, hook_score: float, sentiment_score: float, pause_score: float) -> str:
    """Generates a human-readable one-line reason why the segment was flagged."""
    reasons = []
    
    if hook_score >= 3.0:
        reasons.append("Viral Hook Phrase")
    if energy_score >= 6.0:
        reasons.append("High Speech Energy Spike")
    if pause_score >= 3.0:
        reasons.append("Silence & Tension Setup")
    if sentiment_score >= 3.0:
        reasons.append("Emotional Reaction Peak")

    if not reasons:
        if energy_score > hook_score:
            reasons.append("Excitement & Loud Reaction")
        else:
            reasons.append("High Retention Conversation Segment")

    return " + ".join(reasons[:2])


def analyze_virality(audio_path: str, transcript_segments: list, video_duration: float, target_clips: int = 10):
    """
    Ranks segments by multi-signal virality score and extracts top N non-overlapping candidates.
    Ideal clip length: 15 to 60 seconds.
    """
    sample_rate, energy_map = compute_audio_energy(audio_path)
    
    candidates = []

    # If transcript is empty or minimal, fallback to energy windows
    if not transcript_segments:
        # Generate 30s sliding windows
        window_size = 30
        step = max(10, int(video_duration / (target_clips * 2))) if video_duration > 0 else 15
        for start_t in range(0, max(1, int(video_duration) - window_size), step):
            end_t = start_t + window_size
            window_energies = [energy_map.get(s, 0.0) for s in range(start_t, end_t)]
            avg_e = sum(window_energies) / len(window_energies) if window_energies else 0
            
            score = float(avg_e * 100)
            candidates.append({
                "start": start_t,
                "end": end_t,
                "duration": window_size,
                "score": round(min(99.0, max(50.0, score)), 1),
                "text": "Speech Segment",
                "reason": "High Audio Volume Spike"
            })
    else:
        # Slide window over transcript bounds
        num_segments = len(transcript_segments)
        for i in range(num_segments):
            start_t = transcript_segments[i]["start"]
            
            # Form candidate clips between 15 and 60 seconds
            sub_text = ""
            for j in range(i, num_segments):
                end_t = transcript_segments[j]["end"]
                duration = end_t - start_t
                sub_text += " " + transcript_segments[j]["text"]

                if duration < 14.0:
                    continue
                if duration > 61.0:
                    break

                # Compute 4 core signal scores
                int_start = int(start_t)
                int_end = int(end_t)
                win_energies = [energy_map.get(s, 0.0) for s in range(int_start, int_end + 1)]
                avg_energy = (sum(win_energies) / len(win_energies)) if win_energies else 0.0
                peak_energy = max(win_energies) if win_energies else 0.0
                
                energy_score = (avg_energy * 5.0) + (peak_energy * 5.0)
                hook_score = evaluate_text_hook(sub_text)
                sentiment_score = evaluate_sentiment(sub_text)
                pause_score = evaluate_pre_pause(start_t, energy_map)

                # Length preference score (sweet spot: 25s - 45s)
                length_pref = 1.0 - abs(duration - 35.0) / 45.0
                length_score = max(0.2, length_pref) * 2.0

                composite = (
                    (energy_score * 0.35) +
                    (hook_score * 0.30) +
                    (sentiment_score * 0.20) +
                    (pause_score * 0.15) +
                    length_score
                )

                # Scale score to 60-98 range for user appeal
                final_score = round(min(98.5, max(62.0, composite * 10.0)), 1)
                reason = generate_virality_reason(energy_score, hook_score, sentiment_score, pause_score)

                candidates.append({
                    "start": round(start_t, 2),
                    "end": round(end_t, 2),
                    "duration": round(duration, 1),
                    "score": final_score,
                    "text": sub_text.strip(),
                    "reason": reason
                })

    # Sort candidate clips by score descending
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # Select top N non-overlapping clips
    selected_clips = []
    max_target = max(1, min(20, target_clips))
    for cand in candidates:
        if len(selected_clips) >= max_target:
            break
        
        # Check overlap with existing selected clips
        overlap = False
        for sel in selected_clips:
            # Overlap check
            overlap_start = max(cand["start"], sel["start"])
            overlap_end = min(cand["end"], sel["end"])
            overlap_duration = max(0, overlap_end - overlap_start)
            
            if overlap_duration > 5.0: # Allow max 5s overlap
                overlap = True
                break
                
        if not overlap:
            cand["rank"] = len(selected_clips) + 1
            selected_clips.append(cand)

    # Sort selected clips by start timestamp for clean presentation
    selected_clips.sort(key=lambda x: x["start"])
    # Re-assign ranks 1..N based on virality score
    score_ranked = sorted(selected_clips, key=lambda x: x["score"], reverse=True)
    rank_map = {clip["start"]: i + 1 for i, clip in enumerate(score_ranked)}
    for clip in selected_clips:
        clip["rank"] = rank_map[clip["start"]]

    return selected_clips

