import argparse
import json
import os
import time
from pathlib import Path

import requests


OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"


def load_script(json_path: str) -> str:
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    # Prefer "script" but fall back to other keys if needed
    script = data.get("script") or data.get("text") or data.get("voiceover") or ""
    script = script.strip()
    if not script:
        raise ValueError("No script text found in generated.json (expected key: 'script').")
    return script


def tts_request_stream(
    api_key: str,
    text: str,
    out_path: Path,
    model: str = "gpt-4o-mini-tts",
    voice: str = "alloy",
    fmt: str = "mp3",
    max_retries: int = 6,
    connect_timeout: int = 20,
    read_timeout: int = 180,
) -> None:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "voice": voice,
        "format": fmt,
        "input": text,
    }

    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"TTS attempt {attempt}/{max_retries} (model={model}, voice={voice}, fmt={fmt})")

            with requests.post(
                OPENAI_TTS_URL,
                headers=headers,
                json=payload,
                stream=True,
                timeout=(connect_timeout, read_timeout),
            ) as r:
                # Retryable HTTP statuses
                if r.status_code in (429, 500, 502, 503, 504):
                    msg = r.text[:500]
                    raise RuntimeError(f"Retryable HTTP {r.status_code}: {msg}")

                # Non-retryable errors
                if r.status_code != 200:
                    msg = r.text[:1500]
                    raise RuntimeError(f"HTTP {r.status_code}: {msg}")

                out_path.parent.mkdir(parents=True, exist_ok=True)

                tmp_path = out_path.with_suffix(out_path.suffix + ".part")
                if tmp_path.exists():
                    tmp_path.unlink()

                bytes_written = 0
                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
                            bytes_written += len(chunk)

                if bytes_written < 10_000:
                    # Sanity check: a real mp3 should be larger than this for multi-second audio
                    raise RuntimeError(f"TTS returned too few bytes ({bytes_written}).")

                tmp_path.replace(out_path)
                print(f"✅ Wrote TTS audio: {out_path} ({bytes_written} bytes)")
                return

        except (requests.Timeout, TimeoutError) as e:
            last_err = e
            print(f"⚠️ Timeout on attempt {attempt}: {e}")
        except requests.RequestException as e:
            last_err = e
            print(f"⚠️ Request error on attempt {attempt}: {e}")
        except Exception as e:
            last_err = e
            print(f"⚠️ Error on attempt {attempt}: {e}")

        # Backoff
        sleep_s = min(60, int(2 ** attempt))
        print(f"Retrying in {sleep_s}s...")
        time.sleep(sleep_s)

    raise RuntimeError(f"TTS failed after {max_retries} attempts. Last error: {last_err}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True, help="Path to out/generated.json")
    ap.add_argument("--out", required=True, help="Path to output mp3, e.g. out/voice.mp3")
    ap.add_argument("--model", default="gpt-4o-mini-tts")
    ap.add_argument("--voice", default="alloy")
    ap.add_argument("--format", default="mp3")
    args = ap.parse_args()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY environment variable.")

    text = load_script(args.json)

    out_path = Path(args.out)
    tts_request_stream(
        api_key=api_key,
        text=text,
        out_path=out_path,
        model=args.model,
        voice=args.voice,
        fmt=args.format,
    )


if __name__ == "__main__":
    main()
