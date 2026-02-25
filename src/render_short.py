import argparse
import json
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


def normalize_quotes(text: str) -> str:
    return (
        text.replace("’", "'")
            .replace("‘", "'")
            .replace("“", '"')
            .replace("”", '"')
    )


def escape_drawtext(text: str) -> str:
    """
    Escape for FFmpeg drawtext when text is wrapped in single quotes:
      text='...'
    """
    text = normalize_quotes(text)
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    text = text.replace(":", "\\:")
    text = text.replace("%", "\\%")
    text = text.replace(",", "\\,")
    text = text.replace(";", "\\;")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    text = text.replace("\n", "\\n")
    return text


def wrap_title(title: str, max_chars: int = 28) -> str:
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
    if len(lines) > 3:
        lines = lines[:2] + [" ".join(lines[2:])]
    return "\n".join(lines)


def split_script_into_chunks(script: str, target_chunks: int = 8) -> List[str]:
    s = normalize_quotes(script.strip())
    if not s:
        return []

    parts = [p.strip() for p in s.replace("?", "?.").replace("!", "!.").split(".") if p.strip()]
    if len(parts) <= 1:
        return [s]

    chunks: List[str] = []
    cur = ""
    for sent in parts:
        candidate = (cur + " " + sent).strip()
        if len(candidate) <= 170:
            cur = candidate
        else:
            if cur:
                chunks.append(cur)
            cur = sent
    if cur:
        chunks.append(cur)

    while len(chunks) > target_chunks:
        best_i = 0
        best_len = 10**9
        for i in range(len(chunks) - 1):
            merged_len = len(chunks[i]) + len(chunks[i + 1])
            if merged_len < best_len:
                best_len = merged_len
                best_i = i
        chunks[best_i] = (chunks[best_i] + " " + chunks[best_i + 1]).strip()
        del chunks[best_i + 1]

    return chunks


def allocate_timings(chunks: List[str], total_dur: float, lead_in: float = 0.4, tail_out: float = 0.2) -> List[Tuple[float, float]]:
    available = max(0.5, total_dur - lead_in - tail_out)
    weights = [max(3, len(c.split())) for c in chunks]
    wsum = sum(weights) if weights else 1

    timings = []
    t = lead_in
    for w in weights:
        dt = available * (w / wsum)
        timings.append((t, t + dt))
        t += dt

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

    dur = max(8.0, ffprobe_duration(args.audio))

    title_wrapped = wrap_title(normalize_quotes(title), max_chars=28)
    chunks = split_script_into_chunks(script, target_chunks=8)
    times = allocate_timings(chunks, dur)

    # Animated professional background (subtle)
    bg = (
        f"[0:v][1:v]blend=all_expr='A*(0.55+0.15*sin(2*PI*t/{dur})) + B*(0.45-0.15*sin(2*PI*t/{dur}))',"
        f"noise=alls=12:allf=t+u,"
        f"scale={W+40}:{H+40},crop={W}:{H}:x='20+10*sin(2*PI*t/{dur})':y='20+10*cos(2*PI*t/{dur})'"
        f"[bg]"
    )

    # Title
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

    # Captions: chain with labels + semicolons (NO commas between filters)
    caption_chain_parts = []
    in_label = "v1"
    for i, (chunk, (ts, te)) in enumerate(zip(chunks, times), start=1):
        out_label = f"c{i}"
        c = escape_drawtext(chunk)
        # commas INSIDE expression are fine because we are not using comma-separated filter chains
        enable_expr = f"between(t,{ts:.3f},{te:.3f})"
        caption_chain_parts.append(
            f"[{in_label}]drawtext=fontfile={FONT_REG}:"
            f"text='{c}':"
            f"fontcolor=white:fontsize=48:"
            f"x=(w-text_w)/2:y=1120:"
            f"line_spacing=10:"
            f"box=1:boxcolor=black@0.28:boxborderw=22:"
            f"enable='{enable_expr}'"
            f"[{out_label}]"
        )
        in_label = out_label

    # Progress bar on final caption output
    progress = (
        f"[{in_label}]drawbox=x=120:y=h-140:w=w-240:h=10:color=white@0.10:t=fill,"
        f"drawbox=x=120:y=h-140:w='(w-240)*t/{dur}':h=10:color=#FF7A18@0.95:t=fill"
        f"[vout]"
    )

    filter_complex = ";".join([bg, title_filter] + caption_chain_parts + [progress])

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
