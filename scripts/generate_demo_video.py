#!/usr/bin/env python3
"""
Silicon-Pilot Demo Video Generator
====================================
Pipeline:
  1. edge-tts  → generate per-scene MP3 voiceover clips
  2. ffprobe   → measure exact duration (ms) of each clip
  3. playwright → record a Chromium session, sleeping exactly
                  clip_duration + 1 s between each scene
  4. ffmpeg    → concatenate audio clips, mux with .webm video
                  → docs/silicon_pilot_demo_with_voice.mp4
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ── Project root ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

AUDIO_DIR = ROOT / "_demo_audio"
AUDIO_DIR.mkdir(exist_ok=True)

VIDEO_DIR = ROOT / "_demo_video"
VIDEO_DIR.mkdir(exist_ok=True)

OUTPUT_MP4 = DOCS / "silicon_pilot_demo_with_voice.mp4"

BASE_URL = "http://localhost:8000"

QUERY = (
    "I need an STM32 microcontroller for a high-performance robotics motor controller. "
    "Requires CAN-FD, 2x SPI, 1MB flash, 256KB RAM, FPU, runs at 3.3V, "
    "preferably LQFP-144 package, budget under $10."
)

# ── Voiceover script ──────────────────────────────────────────────────────────
SCENES = [
    {
        "id": 1,
        "text": "Welcome to Silicon Pilot. Today, we are architecting a high-performance robotics controller.",
        "action": "landing",
    },
    {
        "id": 2,
        "text": (
            "Our local AI pipeline instantly translates this query into strict constraints. "
            "It scans our database of four hundred microcontrollers, and ranks the absolute "
            "best architectural candidates."
        ),
        "action": "analyze",
    },
    {
        "id": 3,
        "text": "Let's explore the AI Debate. Two agents argue the technical trade-offs of this chip.",
        "action": "debate",
    },
    {
        "id": 4,
        "text": "The Architect Review provides a senior-level summary of why this microcontroller was chosen.",
        "action": "architect_review",
    },
    {
        "id": 5,
        "text": "The Full Verification panel exposes every raw datasheet parameter for rigorous engineering.",
        "action": "full_detail",
    },
    {
        "id": 6,
        "text": "The Drop-in Replacement engine instantly identifies pin-to-pin compatible alternatives graded by rework severity.",
        "action": "drop_in",
    },
    {
        "id": 7,
        "text": (
            "Power budgeting is critical. We open the Power Profiler, configure the duty cycle, "
            "and Silicon Pilot instantly computes real-world battery life."
        ),
        "action": "power_profiler",
    },
    {
        "id": 8,
        "text": "The Package Analyzer assesses mechanical footprint complexity and flags High Density Interconnect requirements.",
        "action": "package_analysis",
    },
    {
        "id": 9,
        "text": "The Ecosystem RAG recommends perfectly matched companion chips like CAN transceivers and regulators.",
        "action": "ecosystem",
    },
    {
        "id": 10,
        "text": (
            "Now, let's solve pin multiplexing. We demand CAN FD and SPI interfaces. "
            "A Constraint Satisfaction Engine instantly assigns optimal physical pins without conflicts."
        ),
        "action": "pin_mux",
    },
    {
        "id": 11,
        "text": (
            "Finally, we add these to our System BOM. The Validation tool mathematically ensures "
            "that logic levels and interfaces align flawlessly across all components."
        ),
        "action": "bom",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Generate audio clips via edge-tts
# ─────────────────────────────────────────────────────────────────────────────

async def _generate_clip(scene: dict, out_path: Path) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(
        text=scene["text"],
        voice="en-US-GuyNeural",
        rate="+0%",
        volume="+0%",
    )
    await communicate.save(str(out_path))


async def generate_all_audio():
    print("\n[1/4] Generating voiceover clips with edge-tts …")
    tasks = []
    for scene in SCENES:
        out = AUDIO_DIR / f"scene_{scene['id']:02d}.mp3"
        tasks.append(_generate_clip(scene, out))
    await asyncio.gather(*tasks)
    print(f"      ✓ {len(SCENES)} clips saved to {AUDIO_DIR}")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Measure exact durations via ffprobe
# ─────────────────────────────────────────────────────────────────────────────

def get_duration(mp3_path: Path) -> float:
    """Return duration in seconds (float) using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        str(mp3_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)
    return float(info["streams"][0]["duration"])


def measure_durations() -> dict:
    print("\n[2/4] Measuring audio clip durations …")
    durations = {}
    for scene in SCENES:
        mp3 = AUDIO_DIR / f"scene_{scene['id']:02d}.mp3"
        dur = get_duration(mp3)
        durations[scene["id"]] = dur
        print(f"      Scene {scene['id']:02d}: {dur:.3f}s  — {scene['text'][:55]}…")
    return durations


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Playwright browser recording
# ─────────────────────────────────────────────────────────────────────────────

def run_playwright_recording(durations: dict):
    from playwright.sync_api import sync_playwright

    print("\n[3/4] Starting Playwright browser recording …")
    BUFFER = 1.0  # extra seconds after each audio clip

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(VIDEO_DIR),
            record_video_size={"width": 1440, "height": 900},
        )
        page = context.new_page()

        # ── Scene 1: Landing ──────────────────────────────────────────────
        print("  → Scene 1: Landing page")
        page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        time.sleep(durations[1] + BUFFER)

        # ── Scene 2: Analyze requirements ─────────────────────────────────
        print("  → Scene 2: Typing query & analyzing …")
        page.fill("#intentInput", QUERY)
        time.sleep(0.8)
        page.click("button:has-text('Analyze Requirements')")
        # Wait for results to appear (LLM pipeline can be slow)
        page.wait_for_selector("#resultsList .part-card", timeout=120000)
        time.sleep(durations[2] + BUFFER)

        # ── Scene 3: AI Debate ────────────────────────────────────────────
        print("  → Scene 3: AI Debate")
        page.click("button:has-text('Debate')", timeout=10000)
        time.sleep(3)  # let modal animate in
        time.sleep(durations[3] + BUFFER)
        page.evaluate("document.querySelectorAll('[style*=fixed]').forEach(e => e.remove());")
        time.sleep(0.5)

        # ── Scene 4: Architect Review ─────────────────────────────────────
        print("  → Scene 4: Architect Review")
        page.click("button:has-text('Architect Review')", timeout=10000)
        time.sleep(3)
        time.sleep(durations[4] + BUFFER)
        page.evaluate("document.querySelectorAll('[style*=fixed]').forEach(e => e.remove());")
        time.sleep(0.5)

        # ── Scene 5: Full Detail Verification ────────────────────────────
        print("  → Scene 5: Full Detail Verification")
        page.click("button:has-text('Full Detail Verification')", timeout=10000)
        time.sleep(4)
        time.sleep(durations[5] + BUFFER)
        page.evaluate("document.querySelectorAll('[style*=fixed]').forEach(e => e.remove());")
        time.sleep(0.5)

        # ── Scene 6: Drop-in Replacements ────────────────────────────────
        print("  → Scene 6: Drop-in Replacements")
        page.click("button:has-text('Drop-in Replacements')", timeout=10000)
        time.sleep(3)
        time.sleep(durations[6] + BUFFER)
        page.evaluate("document.querySelectorAll('[style*=fixed]').forEach(e => e.remove());")
        time.sleep(0.5)

        # ── Scene 7: Power Profiler ───────────────────────────────────────
        print("  → Scene 7: Power Profiler")
        page.click("button:has-text('Power Profile')", timeout=10000)
        time.sleep(2)
        page.fill("#pp-run-pct", "20")
        time.sleep(0.5)
        try:
            page.check("input.pp-peri[value='can']")
        except Exception:
            pass
        time.sleep(0.5)
        page.click("button:has-text('Calculate Power Profile')", timeout=10000)
        time.sleep(3)
        time.sleep(durations[7] + BUFFER)
        page.evaluate("document.querySelectorAll('[style*=fixed]').forEach(e => e.remove());")
        time.sleep(0.5)

        # ── Scene 8: Package Analysis ─────────────────────────────────────
        print("  → Scene 8: Package Analysis")
        page.click("button:has-text('Package Analysis')", timeout=10000)
        time.sleep(3)
        time.sleep(durations[8] + BUFFER)
        page.evaluate("document.querySelectorAll('[style*=fixed]').forEach(e => e.remove());")
        time.sleep(0.5)

        # ── Scene 9: Ecosystem RAG ────────────────────────────────────────
        print("  → Scene 9: Ecosystem RAG")
        page.click("button:has-text('Ecosystem')", timeout=10000)
        time.sleep(4)
        time.sleep(durations[9] + BUFFER)
        page.evaluate("document.querySelectorAll('[style*=fixed]').forEach(e => e.remove());")
        time.sleep(0.5)

        # ── Scene 10: Pin Mux Solver ──────────────────────────────────────────
        print("  → Scene 10: Pin Mux Solver")
        page.evaluate("document.querySelector('#pm-part-id').scrollIntoView({behavior:'smooth', block:'center'})")
        time.sleep(1.5)
        page.select_option(".req-type", "can")
        time.sleep(0.5)
        # Use JS click to bypass any overlay interception
        page.evaluate("""
            () => {
                const btns = [...document.querySelectorAll('button')];
                const btn = btns.find(b => b.textContent.trim() === '+ Add Peripheral');
                if (btn) btn.click();
            }
        """)
        time.sleep(0.8)
        page.select_option("div.req-row:nth-child(2) .req-type", "spi")
        time.sleep(0.5)
        # JS click for Check Peripheral Availability too
        page.evaluate("""
            () => {
                const btns = [...document.querySelectorAll('button')];
                const btn = btns.find(b => b.textContent.trim() === 'Check Peripheral Availability');
                if (btn) btn.click();
            }
        """)
        time.sleep(3)
        time.sleep(durations[10] + BUFFER)

        # ── Scene 11: System BOM ──────────────────────────────────────────────
        print("  → Scene 11: System BOM")
        # Scroll back to top to click Add to BOM on the first card
        page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        time.sleep(1.2)
        # Use JS click to bypass any overlay on the Add to BOM button
        page.evaluate("""
            () => {
                const btns = [...document.querySelectorAll('button')];
                const btn = btns.find(b => b.textContent.trim() === 'Add to BOM');
                if (btn) btn.click();
            }
        """)
        time.sleep(1.2)
        # Scroll to BOM section and check compatibility
        page.evaluate("document.getElementById('bom-check-btn').scrollIntoView({behavior:'smooth', block:'center'})")
        time.sleep(1.2)
        page.evaluate("""
            () => {
                const btns = [...document.querySelectorAll('button')];
                const btn = btns.find(b => b.textContent.trim().includes('Check Compatibility'));
                if (btn) btn.click();
            }
        """)
        time.sleep(4)
        time.sleep(durations[11] + BUFFER)

        print("  → Closing browser context …")
        context.close()
        browser.close()

    # Locate the recorded .webm file
    webm_files = sorted(VIDEO_DIR.glob("*.webm"))
    if not webm_files:
        raise FileNotFoundError(f"No .webm recording found in {VIDEO_DIR}")
    webm = webm_files[-1]
    print(f"  ✓ Video recorded: {webm}")
    return webm


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Concatenate audio + mux with video via ffmpeg
# ─────────────────────────────────────────────────────────────────────────────

def mux_video_audio(webm_path: Path, durations: dict):
    print("\n[4/4] Muxing audio + video with ffmpeg …")

    # Build a concat list for the audio clips with silence padding
    # Each clip needs: the clip itself + (BUFFER seconds) of silence between scenes
    BUFFER = 1.0
    SILENCE_RATE = 44100
    CHANNELS = 2

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # Generate concat file for ffmpeg
        concat_lines = []
        for scene in SCENES:
            mp3 = AUDIO_DIR / f"scene_{scene['id']:02d}.mp3"
            concat_lines.append(f"file '{mp3.resolve()}'")

            # Add a silence file equal to BUFFER seconds
            silence_dur = BUFFER
            silence_path = tmp / f"silence_{scene['id']:02d}.mp3"
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"anullsrc=r={SILENCE_RATE}:cl=stereo",
                "-t", str(silence_dur),
                "-q:a", "9",
                "-acodec", "libmp3lame",
                str(silence_path),
            ], check=True, capture_output=True)
            concat_lines.append(f"file '{silence_path.resolve()}'")

        concat_file = tmp / "audio_concat.txt"
        concat_file.write_text("\n".join(concat_lines))

        # Concatenate all audio clips into one track
        merged_audio = tmp / "merged_audio.mp3"
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(merged_audio),
        ], check=True, capture_output=True)
        print(f"  ✓ Audio merged: {merged_audio}")

        # Convert merged audio to AAC for MP4 container
        merged_aac = tmp / "merged_audio.aac"
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(merged_audio),
            "-c:a", "aac", "-b:a", "192k",
            str(merged_aac),
        ], check=True, capture_output=True)

        # Mux: video (webm → h264) + audio → mp4
        # Use -shortest to trim to the shorter of video/audio
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(webm_path),
            "-i", str(merged_aac),
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(OUTPUT_MP4),
        ], check=True)  # let output stream so we see ffmpeg progress

    print(f"\n  ✓ Final video: {OUTPUT_MP4}")
    size_mb = OUTPUT_MP4.stat().st_size / (1024 * 1024)
    print(f"  ✓ File size:   {size_mb:.1f} MB")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # Verify server is reachable before starting
    import urllib.request
    print("Verifying server at http://localhost:8000 …")
    for attempt in range(12):
        try:
            urllib.request.urlopen("http://localhost:8000", timeout=5)
            print("  ✓ Server is reachable\n")
            break
        except Exception:
            if attempt == 11:
                sys.exit("ERROR: Server at localhost:8000 is not responding. Start it first.")
            print(f"  ⏳ Waiting for server … ({attempt + 1}/12)")
            time.sleep(5)

    # Run pipeline
    asyncio.run(generate_all_audio())
    durations = measure_durations()
    webm_path = run_playwright_recording(durations)
    mux_video_audio(webm_path, durations)

    print("\n" + "=" * 60)
    print("  VIDEO READY:")
    print(f"  {OUTPUT_MP4}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
