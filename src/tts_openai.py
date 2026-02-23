import argparse
import json
import os
import urllib.request

TTS_URL = "https://api.openai.com/v1/audio/speech"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True, help="generated.json from openai_generate.py")
    ap.add_argument("--out", required=True, help="output mp3 path")
    args = ap.parse_args()

    api_key = os.environ["OPENAI_API_KEY"]

    data = json.loads(open(args.json, "r", encoding="utf-8").read())
    script = data.get("script", "").strip()
    if not script:
        raise SystemExit("No script found in JSON.")

    payload = {
        "model": "gpt-4o-mini-tts",
        "voice": "alloy",
        "format": "mp3",
        "input": script
    }

    req = urllib.request.Request(
        TTS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        audio_bytes = resp.read()

    with open(args.out, "wb") as f:
        f.write(audio_bytes)

    print(f"✅ Wrote voice MP3: {args.out}")

if __name__ == "__main__":
    main()
