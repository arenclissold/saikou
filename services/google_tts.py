# Audio generation service using Google Gemini TTS

import os
import hashlib
import json
import base64
import re
import urllib.request
import urllib.error
import wave
from typing import Optional

from aqt import mw
from ..utils import get_config


def get_api_key() -> str:
    """Get the Google API key from local config/defaults."""
    config = get_config()
    return config.get("google_api_key", "")


def get_tts_model() -> str:
    """Get the TTS model from config."""
    config = get_config()
    return config.get("tts_model", "gemini-3.1-flash-tts-preview")


def get_tts_voice() -> str:
    """Get the TTS voice from config."""
    config = get_config()
    return config.get("tts_voice", "Kore")


def get_media_folder() -> str:
    """Get the Anki media folder path."""
    return mw.col.media.dir()


def generate_audio_filename(text: str, prefix: str = "saikou") -> str:
    """
    Generate a unique filename for audio based on text content.

    Args:
        text: The text being converted to speech
        prefix: Prefix for the filename

    Returns:
        A unique filename like 'saikou_abc123.wav'
    """
    # Create a hash of the text for uniqueness
    text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{text_hash}.wav"


def _get_audio_part_data(part: dict) -> tuple[Optional[bytes], str]:
    """Extract base64 audio bytes and MIME type from a Gemini response part."""
    inline_data = part.get("inlineData") or part.get("inline_data")
    if not inline_data:
        return None, ""

    data = inline_data.get("data")
    if not data:
        return None, inline_data.get("mimeType") or inline_data.get("mime_type") or ""

    audio_data = base64.b64decode(data) if isinstance(data, str) else data
    mime_type = inline_data.get("mimeType") or inline_data.get("mime_type") or ""
    return audio_data, mime_type


def _get_sample_rate(mime_type: str) -> int:
    """Extract sample rate from a MIME type, falling back to Gemini TTS default."""
    match = re.search(r"rate=(\d+)", mime_type)
    if match:
        return int(match.group(1))
    return 24000


def _write_audio_file(path: str, audio_data: bytes, mime_type: str) -> None:
    """Write Gemini TTS audio to disk in a playable format."""
    if "wav" in mime_type.lower():
        with open(path, "wb") as f:
            f.write(audio_data)
        return

    # Gemini TTS defaults to LINEAR16/PCM. Wrap it in a WAV container so Anki can play it.
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_get_sample_rate(mime_type))
        wf.writeframes(audio_data)


def generate_audio(text: str, filename: Optional[str] = None) -> str:
    """
    Generate audio using Google Gemini TTS and save to Anki media folder.

    Args:
        text: The text to convert to speech
        filename: Optional custom filename (without path)

    Returns:
        The filename of the saved audio file (for use in [sound:] tags)

    Raises:
        ValueError: If API key not configured
        Exception: If API request fails
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("Google API key not configured. Please set it in the add-on config.")

    if not filename:
        filename = generate_audio_filename(text)

    # Prepare the request using Gemini API
    model = get_tts_model()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json",
    }

    voice_name = get_tts_voice()

    payload = {
        "contents": [{
            "parts": [{
                "text": text
            }]
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice_name
                    }
                }
            }
        }
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))

        # Extract audio from Gemini response.
        if "candidates" not in result or len(result["candidates"]) == 0:
            raise Exception(f"No candidates in Gemini TTS response. Full response: {json.dumps(result)}")

        candidate = result["candidates"][0]

        # Check for finish reason and handle it
        finish_reason = candidate.get("finishReason", "UNKNOWN")
        if finish_reason != "STOP":
            raise Exception(f"TTS generation stopped with reason: {finish_reason}. Candidate: {json.dumps(candidate)}")

        if "content" not in candidate:
            raise Exception(f"No 'content' in candidate despite STOP finish reason. Candidate: {json.dumps(candidate)}")

        if "parts" not in candidate["content"]:
            raise Exception(f"No 'parts' in content. Content keys: {candidate['content'].keys()}, Content: {json.dumps(candidate['content'])[:200]}")

        parts = candidate["content"]["parts"]
        audio_data = None
        mime_type = ""

        for part in parts:
            audio_data, mime_type = _get_audio_part_data(part)
            if audio_data:
                break

        if not audio_data:
            raise Exception(f"No audio data in Gemini TTS response. Parts structure: {json.dumps(parts)[:500]}")

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise Exception(f"Google Gemini TTS API error ({e.code}): {error_body}")
    except urllib.error.URLError as e:
        raise Exception(f"Network error: {e.reason}")

    # Save to media folder
    media_path = os.path.join(get_media_folder(), filename)
    _write_audio_file(media_path, audio_data, mime_type)

    # Register with Anki's media manager
    mw.col.media.add_file(media_path)

    return filename


def generate_word_audio(word: str) -> str:
    """
    Generate audio for a single word.

    Args:
        word: The word to generate audio for

    Returns:
        The sound tag string like '[sound:filename.wav]'
    """
    filename = generate_audio_filename(word, prefix="saikou_word")
    filename = generate_audio(word, filename)
    return f"[sound:{filename}]"


def generate_sentence_audio(sentence: str) -> str:
    """
    Generate audio for a sentence.

    Args:
        sentence: The sentence to generate audio for

    Returns:
        The sound tag string like '[sound:filename.wav]'
    """
    filename = generate_audio_filename(sentence, prefix="saikou_sentence")
    filename = generate_audio(sentence, filename)
    return f"[sound:{filename}]"


def audio_file_exists(filename: str) -> bool:
    """
    Check if an audio file already exists in the media folder.

    Args:
        filename: The filename to check

    Returns:
        True if the file exists
    """
    media_path = os.path.join(get_media_folder(), filename)
    return os.path.exists(media_path)
