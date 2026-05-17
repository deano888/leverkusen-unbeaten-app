"""
voice_generator.py
==================
Generates ElevenLabs audio for all commentary in statsbomb_cache/commentary.csv
Saves MP3 files to statsbomb_cache/audio/

Run ONCE per match after commentary_generator.py:
    py voice_generator.py                    # generate all missing audio
    py voice_generator.py --match Augsburg   # generate one match only
    py voice_generator.py --list-voices      # show available voices

Requires: pip install elevenlabs
Sign up free at elevenlabs.io — free tier gives ~10 min/month which covers all 10 matches.
"""

import os, argparse, time
import pandas as pd


def score_to_words(text):
    """Convert 2-1 -> two-one, 3-0 -> three-nil for natural TTS pronunciation."""
    import re
    nums = {"0":"nil","1":"one","2":"two","3":"three","4":"four",
            "5":"five","6":"six","7":"seven","8":"eight","9":"nine"}
    def replace(m):
        hw = nums.get(m.group(1), m.group(1))
        aw = nums.get(m.group(2), m.group(2))
        return f"{hw} all" if m.group(1)==m.group(2) else f"{hw}-{aw}"
    return re.sub(r"([0-9])-([0-9])", replace, text)

CACHE_DIR  = "statsbomb_cache"
AUDIO_DIR  = f"{CACHE_DIR}/audio"
COMMENTARY = f"{CACHE_DIR}/commentary.csv"

# ElevenLabs voice settings
# Good sports commentator voices to try:
#   "Adam"    — deep, authoritative broadcast
#   "Antoni"  — warm, conversational
#   "Josh"    — energetic, younger pundit feel
#   "Arnold"  — powerful, dramatic
VOICE_NAME = "Adam"
MODEL_ID   = "eleven_monolingual_v1"

def slugify(home, away, content_type, idx):
    """Create a safe filename."""
    h = home.replace(" ","_").replace("'","")
    a = away.replace(" ","_").replace("'","")
    return f"{h}_vs_{a}_{content_type}_{idx}.mp3"

_API_KEY = None

def get_api_key():
    global _API_KEY
    if not _API_KEY:
        _API_KEY = os.environ.get("ELEVENLABS_API_KEY","").strip()
    if not _API_KEY:
        _API_KEY = input("Paste your ElevenLabs API key: ").strip()
    return _API_KEY

def get_voice_id(voice_name):
    """Find voice ID by name or return directly if already an ID."""
    import requests as req
    resp = req.get(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": get_api_key()}
    )
    voices = resp.json().get("voices", [])

    # Try exact name match first
    for v in voices:
        if v["name"].lower() == voice_name.lower():
            print(f"  Found voice: {v['name']} ({v['voice_id']})")
            return v["voice_id"]

    # If it looks like an ID (long string), use it directly
    if len(voice_name) > 15:
        print(f"  Using voice ID directly: {voice_name}")
        return voice_name

    # Show all available voices clearly
    print(f"Voice '{voice_name}' not found.")
    print("Your available voices:")
    for v in voices:
        print(f"  Name: {v['name']:<30} ID: {v['voice_id']}")
    print("Options: 1) type exact name  2) paste voice ID")
    choice = input("Enter voice name or ID: ").strip()
    print("  1. Type exact voice name  2. Paste the voice ID")
    choice = input("Enter voice name or ID: ").strip()
    return get_voice_id(choice)


def generate_audio(voice_id, text, out_path):
    """Generate and save MP3 using REST API — no SDK needed."""
    import requests as req
    resp = req.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={
            "xi-api-key": get_api_key(),
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        json={
            "text": text,
            "model_id": MODEL_ID,
            "voice_settings": {
                "stability": 0.4,
                "similarity_boost": 0.85,
                "style": 0.3,
                "use_speaker_boost": True
            }
        }
    )
    if resp.status_code != 200:
        raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")
    with open(out_path, "wb") as f:
        f.write(resp.content)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--match",       type=str, default=None, help="Filter by opponent")
    parser.add_argument("--list-voices", action="store_true",    help="List available voices")
    parser.add_argument("--voice",       type=str, default=VOICE_NAME, help=f"Voice name (default: {VOICE_NAME})")
    args = parser.parse_args()

    os.makedirs(AUDIO_DIR, exist_ok=True)

    if not os.path.exists(COMMENTARY):
        print("No commentary.csv found. Run commentary_generator.py first.")
        return

    df = pd.read_csv(COMMENTARY)

    get_api_key()   # prompt once at start
    voice_id = get_voice_id(args.voice)
    print(f"\nUsing voice: {args.voice} ({voice_id})\n")

    if args.list_voices:
        return

    # Filter matches
    if args.match:
        df = df[
            df["home_fd"].str.contains(args.match, case=False, na=False) |
            df["away_fd"].str.contains(args.match, case=False, na=False)
        ]

    if df.empty:
        print("No commentary found.")
        return

    total = len(df)
    generated = 0
    skipped   = 0
    errors    = 0

    for _, row in df.iterrows():
        home  = str(row["home_fd"])
        away  = str(row["away_fd"])
        ctype = str(row["content_type"])
        idx   = int(row["highlight_idx"])
        text  = str(row["commentary"])

        if not text or len(text) < 5 or text == "nan":
            skipped += 1
            continue

        fname    = slugify(home, away, ctype, idx)
        out_path = os.path.join(AUDIO_DIR, fname)

        if os.path.exists(out_path):
            print(f"  ✓ Already exists: {fname}")
            skipped += 1
            continue

        label = f"{home} vs {away} | {ctype} #{idx}"
        print(f"  🎙️  Generating: {label}")
        print(f"       \"{text[:70]}{'...' if len(text)>70 else ''}\"")

        try:
            clean_text = score_to_words(text)
            generate_audio(voice_id, clean_text, out_path)
            size_kb = os.path.getsize(out_path) // 1024
            print(f"       ✓ Saved {fname} ({size_kb}KB)")
            generated += 1
        except Exception as e:
            print(f"       ✗ Error: {e}")
            errors += 1

        time.sleep(0.5)   # be polite to the API

    print(f"\nDone! Generated: {generated} | Skipped: {skipped} | Errors: {errors}")
    print(f"Audio files saved to: {AUDIO_DIR}/")

    # Show estimated credit usage
    chars = df["commentary"].dropna().apply(lambda x: len(str(x))).sum()
    print(f"\nElevenLabs credit usage: ~{chars:,} characters")
    print(f"Free tier gives 10,000 chars/month. You used ~{chars} for this batch.")

if __name__ == "__main__":
    main()
