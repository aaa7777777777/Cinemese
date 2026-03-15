"""
api/chat.py + voice.py combined
Multimodal API calls: chat → CharacterMoment, voice → audio bytes
"""

from __future__ import annotations
import os
import json
import httpx
from pathlib import Path
from typing import Optional


ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
MODEL = "claude-opus-4-5"


# ─────────────────────────────────────────────
# chat.py — generate a CharacterMoment
# ─────────────────────────────────────────────

def generate_moment(
    system_prompt: str,
    user_turn: str,
    max_tokens: int = 300,
) -> str:
    """
    Calls Anthropic API with the assembled prompt.
    Returns raw text — the CharacterMoment as the model wrote it.
    """
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_turn}],
        },
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    return data["content"][0]["text"]


def generate_skill_content(
    system_prompt: str,
    skill_type: str,
    event_description: Optional[str],
    emotion_color: str,
    max_chars: int = 80,
) -> str:
    """
    Generates short in-character content for a skill widget.
    skill_type: push_note | float_bubble | intrusive_thought | etc.
    """
    skill_instructions = {
        "push_note": (
            f"Write one sentence (max {max_chars} chars) this character would send "
            f"as a push notification. Not a greeting. Something they noticed or thought. "
            f"Voiced completely in character."
        ),
        "float_bubble": (
            f"Write a fragment (max {max_chars} chars) that floats on screen for 5 seconds. "
            f"Incomplete is fine. Not explanatory."
        ),
        "intrusive_thought": (
            f"Write one thought (max {max_chars} chars) that surfaces uninvited. "
            f"Late night register. The real thing, not the performance of it."
        ),
        "timed_reminder": (
            f"Write a single observation (max {max_chars} chars). "
            f"Time-of-day appropriate. In the character's voice."
        ),
    }

    instruction = skill_instructions.get(skill_type, f"Write something. Max {max_chars} chars.")

    context_parts = [f"Emotional state: {emotion_color}."]
    if event_description:
        context_parts.append(f"Something that happened: {event_description}")

    user_turn = "\n".join(context_parts) + "\n\n" + instruction

    return generate_moment(system_prompt, user_turn, max_tokens=60)


# ─────────────────────────────────────────────
# voice.py — text to audio
# ─────────────────────────────────────────────

def synthesize(
    text: str,
    voice_id: str,
    speaking_rate: float = 1.0,
    output_path: Optional[Path] = None,
) -> bytes:
    """
    Calls ElevenLabs TTS. Returns audio bytes.
    If output_path given, also writes to file.
    """
    if not ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY not set")

    # Empty speech = silence. Return 1s of silence (44 bytes WAV header placeholder)
    if not text or not text.strip():
        return b"\x00" * 44

    response = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "content-type": "application/json",
        },
        json={
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {
                "stability":        0.55,
                "similarity_boost": 0.75,
                "speed":            speaking_rate,
            },
        },
        timeout=20.0,
    )
    response.raise_for_status()
    audio = response.content

    if output_path:
        output_path.write_bytes(audio)

    return audio


def synthesize_moment(
    moment_text: Optional[str],
    voice_profile: dict,
    output_path: Optional[Path] = None,
) -> Optional[bytes]:
    """
    Synthesizes speech from a CharacterMoment.speech field.
    Returns None if the moment is silent (no speech).
    """
    if not moment_text:
        # Silence is not an error — it is the output
        return None

    voice_id      = voice_profile.get("voice_id")
    speaking_rate = voice_profile.get("speaking_rate", 1.0)

    if not voice_id:
        return None

    return synthesize(moment_text, voice_id, speaking_rate, output_path)
