import argparse
import json
import subprocess
from pathlib import Path

def run(cmd):
    print(" ".join(cmd))
    subprocess.check_call(cmd)

def escape_text(text: str) -> str:
    # Escape characters for FFmpeg drawtext
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "\\'")
    text = text.replace("%", "\\%")
    return text

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = json.loads(open(args.json, "r", encoding="utf-8").read())
    title = data.get("youtube_title", "Finance Update")

    safe_title = escape_text(title)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    drawtext = (
        "drawtext="
        "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{safe_title}':"
        "fontcolor=white:"
        "fontsize=60:"
        "x=(w-text_w)/2:"
        "y=(h-text_h)/2:"
        "box=1:"
        "boxcolor=black@0.4:"
        "boxborderw=30"
    )

    run([
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", "color=c=#0B1F33:s=1080x1920:r=30",
        "-i", args.audio,
        "-vf", drawtext,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        str(out)
    ])

    print(f"✅ Rendered MP4: {out}")

if __name__ == "__main__":
    main()
