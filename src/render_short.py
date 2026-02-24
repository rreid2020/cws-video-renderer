import argparse
import json
import math
import subprocess
from pathlib import Path
from typing import List, Tuple

W, H, FPS = 1080, 1920, 30

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def run(cmd: List[str]) -> None:
    print(" ".join(cmd))
    subprocess.check_call(cmd)


def ffprobe_duration(audio_path: str) -> float:
    # Returns duration in seconds (float)
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        text=True,
    ).strip()
    return float(out)


def escape_drawtext(text: str) -> str:
    # Escape for FFmpeg drawtext
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "\\'")
    text = text.replace("%", "\\%")
    text = text.replace("\n", "\\n")
    return text


def wrap_title(title: str, max_chars: int = 28) -> str:
    # Simple word-wrap into 1–3 lines
    words = title.split()
    lines = []
    cur = ""
    for w in words:
        if len(cur) + (1 if cur else 0) + len(w) <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    # Limit to 3 lines; if longer, merge tail
    if len(lines) > 3:
        lines = lines[:2] + [" ".join(lines[2:])]
    return "\n".join(lines)


def split_script_into_chunks(script: str, target_chunks: int = 8) -> List[str]:
    # Split on sentences first; then merge into ~target_chunks blocks
    s = script.strip()

    # remove disclaimer from captions if present (keep it in audio)
    # We'll try to keep last sentence, but captions look better without a legal line.
    # If you WANT the disclaimer on screen later, we can add it as final chunk.
    parts = [p.strip() for p in s.replace("?", "?.").replace("!", "!.").split(".") if p.strip()]
    sentences = [p if p.endswith(("?", "!", ".")) else p for p in parts]
    if len(sentences) <= 1:
        return [s]

    # Merge sentences into chunk blocks
    chunks: List[str] = []
    cur = ""
    for sent in sentences:
        candidate = (cur + " " + sent).strip()
        # keep blocks readable
        if len(candidate) <= 170:
            cur = candidate
        else:
            if cur:
                chunks.append(cur)
            cur = sent
    if cur:
        chunks.append(cur)

    # If too many chunks, merge nearest until target
    while len(chunks) > target_chunks:
        # merge the two smallest adjacent chunks
        best_i = None
        best_len = None
        for i in range(len(chunks) - 1):
            merged_len = len(chunks[i]) + len(chunks[i + 1])
            if best_len is None or merged_len < best_len:
                best_len = merged_len
                best_i = i
        i = best_i if best_i is not None else 0
        chunks[i] = (chunks[i] + " " + chunks[i + 1]).strip()
        del chunks[i + 1]

    return chunks


def allocate_timings(chunks: List[str], total_dur: float, lead_in: float = 0.4, tail_out: float = 0.2) -> List[Tuple[float, float]]:
    # Allocate time proportionally to word counts
    available = max(0.5, total_dur - lead_in - tail_out)
    weights = []
    for c in chunks:
        weights.append(max(3, len(c.split())))

    wsum = sum(weights)
    timings = []
    t = lead_in
    for w in weights:
        dt = available * (w / wsum)
        timings.append((t, t + dt))
        t += dt
    # Clamp last end
    if timings:
        timings[-1] = (timings[-1][0], min(total_dur - 0.05, timings[-1][1]))
    return timings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = json.loads(Path(args.json).read_text(encoding="utf-8"))
    title = data.get("youtube_title") or "Canadian Finance"
    script = data.get("script") or ""

    dur = ffprobe_duration(args.audio)
    dur = float(max(8.0, dur))

    title_wrapped = wrap_title(title, max_chars=28)
    chunks = split_script_into_chunks(script, target_chunks=8)
    times = allocate_timings(chunks, dur)

    # ----- Background (animated gradient + subtle noise + slow zoom) -----
    # We create two color layers and blend them with moving opacity, then add light noise.
    # This keeps it professional (not flashy).
    #
    # Base inputs:
    #   [0:v] = color #0B1F33
    #   [1:v] = color #081827
    #
    # Then blend w/ a time-varying factor, add noise, and a tiny zoom/pan illusion using scale+crop.
    bg = (
        f"[0:v][1:v]blend=all_expr='A*(0.55+0.15*sin(2*PI*t/{dur})) + B*(0.45-0.15*sin(2*PI*t/{dur}))',"
        f"noise=alls=12:allf=t+u,"
        f"scale={W+40}:{H+40},crop={W}:{H}:x='20+10*sin(2*PI*t/{dur})':y='20+10*cos(2*PI*t/{dur})'"
        f"[bg]"
    )

    # ----- Title block (top safe, centered, boxed) -----
    safe_title = escape_drawtext(title_wrapped)
    title_filter = (
        f"[bg]drawtext=fontfile={FONT_BOLD}:"
        f"text='{safe_title}':"
        f"fontcolor=white:fontsize=64:"
        f"x=(w-text_w)/2:y=180:"
        f"line_spacing=12:"
        f"box=1:boxcolor=black@0.35:boxborderw=28"
        f"[v1]"
    )

    # ----- Caption block (changes over time) -----
    # We'll draw one block per chunk with enable='between(t,start,end)'
    caption_filters = []
    for (chunk, (ts, te)) in zip(chunks, times):
        c = escape_drawtext(chunk)
        # slightly smaller than title; placed mid-lower
        caption_filters.append(
            "drawtext="
            f"fontfile={FONT_REG}:"
            f"text='{c}':"
            f"fontcolor=white:fontsize=48:"
            f"x=(w-text_w)/2:y=1120:"
            f"line_spacing=10:"
            f"box=1:boxcolor=black@0.28:boxborderw=22:"
            f"enable='between(t,{ts:.3f},{te:.3f})'"
        )

    captions_chain = ",".join(caption_filters) if caption_filters else "null"

    # ----- Progress bar (bottom) -----
    # Orange bar + subtle gray track. Width grows with time.
    progress = (
        f"drawbox=x=120:y=h-140:w=w-240:h=10:color=white@0.10:t=fill,"
        f"drawbox=x=120:y=h-140:w='(w-240)*t/{dur}':h=10:color=#FF7A18@0.95:t=fill"
    )

    # Build full filter_complex
    # Inputs:
    # 0: color #0B1F33
    # 1: color #081827
    filter_complex = (
        f"{bg};"
        f"{title_filter};"
        f"[v1]{captions_chain},{progress}[vout]"
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=#0B1F33:s={W}x{H}:r={FPS}",
        "-f", "lavfi", "-i", f"color=c=#081827:s={W}x{H}:r={FPS}",
        "-i", args.audio,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "2:a",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-c:a", "aac",
        "-shortest",
        str(out)
    ])

    print(f"✅ Rendered MP4: {out}")


if __name__ == "__main__":
    main()
