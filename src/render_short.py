import argparse
import json
import subprocess
from pathlib import Path

def run(cmd):
    print(" ".join(cmd))
    subprocess.check_call(cmd)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = json.loads(open(args.json, "r", encoding="utf-8").read())
    title = data.get("youtube_title", "CWS Finance")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Render a 1080x1920 video whose length matches audio (-shortest)
    drawtext = (
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{title.replace(':',' - ').replace(\"'\", \"\\'\")}':"
        "fontcolor=white:fontsize=56:"
        "x=(w-text_w)/2:y=(h-text_h)/2:"
        "box=1:boxcolor=black@0.35:boxborderw=24"
    )

    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=#0B1F33:s=1080x1920:r=30",
        "-i", args.audio,
        "-vf", drawtext,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        str(out)
    ])

    print(f"✅ Rendered MP4: {out}")

if __name__ == "__main__":
    main()
