"""
voice_loader.py
===============
Loads cached MP3 audio files for playback in Streamlit.
Used by app.py to play commentary during highlights.
"""

import os
import base64
import streamlit as st

CACHE_DIR = "statsbomb_cache"
AUDIO_DIR = f"{CACHE_DIR}/audio"


def _slugify(home, away, content_type, idx):
    h = home.replace(" ", "_").replace("'", "")
    a = away.replace(" ", "_").replace("'", "")
    return f"{h}_vs_{a}_{content_type}_{idx}.mp3"


def _audio_path(home, away, content_type, idx):
    fname = _slugify(home, away, content_type, idx)
    return os.path.join(AUDIO_DIR, fname)


def has_audio(home, away, content_type="intro", idx=-1):
    """Return True if audio file exists for this content."""
    return os.path.exists(_audio_path(home, away, content_type, idx))


def get_audio_b64(home, away, content_type="intro", idx=-1):
    """Return base64-encoded MP3 for embedding in HTML."""
    path = _audio_path(home, away, content_type, idx)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def play_audio(home, away, content_type="intro", idx=-1, autoplay=True, dialog_key=""):
    """
    Render an audio player in Streamlit.
    dialog_key makes each dialog session unique so old audio is replaced not stacked.
    Returns True if audio was found and rendered.
    """
    b64 = get_audio_b64(home, away, content_type, idx)
    if not b64:
        return False

    autoplay_attr = "autoplay" if autoplay else ""
    # Unique element id stops browser caching the old audio element
    uid = f"{home}_{away}_{content_type}_{idx}_{dialog_key}".replace(" ","_")
    st.markdown(
        f'<audio id="audio_{uid}" {autoplay_attr} style="display:none;">'
        f'<source src="data:audio/mp3;base64,{b64}" type="audio/mp3">'
        f'</audio>',
        unsafe_allow_html=True,
    )
    return True


def play_audio_visible(home, away, content_type="intro", idx=-1):
    """
    Render a visible audio player (with controls) for testing.
    """
    b64 = get_audio_b64(home, away, content_type, idx)
    if not b64:
        st.caption("No audio available")
        return False

    st.markdown(
        f'<audio controls style="width:100%;margin:4px 0;">'
        f'<source src="data:audio/mp3;base64,{b64}" type="audio/mp3">'
        f'</audio>',
        unsafe_allow_html=True,
    )
    return True


def list_available_audio(home, away):
    """Return list of (content_type, idx) tuples for available audio."""
    available = []
    # Check intro
    if has_audio(home, away, "intro", -1):
        available.append(("intro", -1))
    # Check highlights 0–9
    for i in range(10):
        if has_audio(home, away, "highlight", i):
            available.append(("highlight", i))
    return available


def get_audio_duration(home, away, content_type='intro', idx=-1, fallback=5.0):
    """Read MP3 frame headers for accurate duration. Falls back to size estimate."""
    path = _audio_path(home, away, content_type, idx)
    if not os.path.exists(path):
        return fallback
    try:
        with open(path, 'rb') as f:
            data = f.read()
        offset = 0
        if data[:3] == b'ID3':
            sz = (data[6]<<21)|(data[7]<<14)|(data[8]<<7)|data[9]
            offset = sz + 10
        duration = 0.0
        i = offset
        bitrates = [0,32,40,48,56,64,80,96,112,128,160,192,224,256,320,0]
        samples  = [44100,48000,32000,0]
        while i < len(data) - 4:
            if data[i] == 0xFF and (data[i+1] & 0xE0) == 0xE0:
                try:
                    b1, b2 = data[i+1], data[i+2]
                    br = bitrates[(b2>>4)&0xF] * 1000
                    sr = samples[(b2>>2)&0x3]
                    if br > 0 and sr > 0:
                        frame_size = int(144 * br / sr) + ((b2>>1)&1)
                        duration += 1152 / sr
                        i += frame_size
                        continue
                except Exception:
                    pass
            i += 1
        if duration > 0:
            return round(duration + 0.8, 1)
        return round(len(data) / (128 * 1024 / 8) + 0.8, 1)
    except Exception:
        return fallback
