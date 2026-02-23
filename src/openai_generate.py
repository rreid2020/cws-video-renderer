import argparse
import json
import os
import urllib.request

OPENAI_URL = "https://api.openai.com/v1/chat/completions"

SYSTEM = """You write short-form YouTube Shorts scripts for Canadian personal finance and tax topics.
Style: clear, confident, neutral, non-clickbaity, no mention of RPC, no personal advice, include a brief disclaimer.
Target length: 60–75 seconds spoken (~140–180 words)."""

def call_openai(api_key: str, topic: str) -> dict:
    user = f"""Create a YouTube Short package for this topic:

TOPIC: {topic}

Return STRICT JSON with keys:
youtube_title (max 80 chars),
youtube_description (max 500 chars),
script (140-180 words, spoken voiceover, include a 1-sentence disclaimer at end).
"""

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user}
        ],
        "temperature": 0.7,
    }

    req = urllib.request.Request(
        OPENAI_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    text = data["choices"][0]["message"]["content"].strip()

    # Sometimes models wrap JSON in ```json ...```
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()

    return json.loads(text)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True)
    ap.add_argument("--out", default="out/generated.json")
    args = ap.parse_args()

    api_key = os.environ["OPENAI_API_KEY"]
    result = call_openai(api_key, args.topic)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("✅ Generated content:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
