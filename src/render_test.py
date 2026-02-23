import os, subprocess
from pathlib import Path

def run(cmd):
    print(" ".join(cmd))
    subprocess.check_call(cmd)

def main():
    outdir = Path("out")
    outdir.mkdir(parents=True, exist_ok=True)

    video = outdir / "video.mp4"

    # 1080x1920 vertical, 6 seconds, dark background, moving bar
    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=#0B1F33:s=1080x1920:d=6",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
        "-vf",
        "drawbox=x=0:y=h-120:w=t*180:h=40:color=red@0.9:t=fill,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "text='CWS Automation Render Test':fontcolor=white:fontsize=56:"
        "x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        str(video)
    ])

    print("Rendered:", video)

if __name__ == "__main__":
    main()
