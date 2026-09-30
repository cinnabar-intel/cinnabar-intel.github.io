#!/usr/bin/env python3
"""Generate newsletter issue images via Gemini 2.5 Flash Image (Nano Banana).

Usage:
    python scripts/gen-newsletter-images.py <issue-date>

Reads GEMINI_API_KEY from repo-root .env. Writes PNGs to
knowledge-system/publishing/newsletter/images/<issue-date>/.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

env_path = REPO / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    sys.exit("ERROR: GEMINI_API_KEY not set in env or .env")

MODEL = "gemini-2.5-flash-image"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

ISSUE_DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-04-21"
OUT_DIR = REPO / f"knowledge-system/publishing/newsletter/images/{ISSUE_DATE}"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROMPTS = {
    "hero-defender-first": (
        "Editorial illustration for a senior-executive AI strategy newsletter, 16:9 aspect ratio. "
        "Two ornate vault doors floating in clean negative space against a soft off-white background — "
        "one door subtly marked with a stylized 'A' insignia, the other with a stylized 'O' insignia, "
        "both sealed with glowing cool-blue locks. A single slender silver key silhouette suspended "
        "between them, implying coordination rather than secrecy. Muted navy, deep charcoal, and a "
        "single cool-blue accent. Minimalist, lots of whitespace, editorial magazine aesthetic — "
        "think Stratechery cover, not cyberpunk. No text, no typography, no labels. "
        "Publication-grade illustration with subtle texture, not flat vector."
    ),
    "timeline-two-labs": (
        "Clean minimalist editorial timeline infographic, 16:9 aspect ratio, on off-white background. "
        "A single thin horizontal navy line spans the center. Two small filled circle markers on the "
        "line — a left marker labeled 'APR 14' and a right marker labeled 'APR 17' in small elegant "
        "serif date typography. Above the left marker, a small rounded badge in deep navy reading "
        "'CLAUDE MYTHOS  ·  WITHHELD' in tiny uppercase sans-serif. Above the right marker, a matching "
        "badge reading 'GPT-5.4-CYBER  ·  RESTRICTED'. Faint cool-gray grid in the background, mostly "
        "invisible. A single tiny orange accent dot placed thoughtfully. Editorial newsletter aesthetic, "
        "no clutter, generous whitespace, publication-grade."
    ),
    "compute-inflection": (
        "Minimalist editorial line chart, 16:9 aspect ratio, on off-white background. A single clean "
        "navy line rises sharply from a point labeled '$2.75' on the left to '$4.08' on the right, "
        "with a faint dotted continuation extending upward off the frame. A small annotation near "
        "the top reads 'Blackwell spot rate · USD / H200-hour' in tiny sans-serif. A subtle vertical "
        "gray dashed line midway down the chart labeled 'FEB → APR 2026'. One pale yellow accent "
        "highlight behind the rising segment of the line. Very minimal axis ticks, no gridlines. "
        "Publication-grade editorial chart in the style of The Economist or Financial Times — "
        "flat, clean, confident, lots of whitespace."
    ),
}


def call_gemini(prompt: str) -> dict:
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={"x-goog-api-key": API_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {body_text[:1000]}", file=sys.stderr)
        raise


def save_image(name: str, data: dict) -> Path | None:
    for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        inline = part.get("inlineData") or part.get("inline_data")
        if inline:
            out = OUT_DIR / f"{name}.png"
            out.write_bytes(base64.b64decode(inline["data"]))
            return out
    return None


for name, prompt in PROMPTS.items():
    print(f"[{name}] generating...")
    data = call_gemini(prompt)
    path = save_image(name, data)
    if path:
        print(f"  saved {path} ({path.stat().st_size:,} bytes)")
    else:
        print(f"  WARN: no image part returned")
        print(json.dumps(data, indent=2)[:1500])

print(f"\nDone. Images in: {OUT_DIR}")
