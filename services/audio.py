# Audio generation service using OpenAI TTS

import os
import hashlib
import json
import urllib.request
import urllib.error
from typing import Optional

from aqt import mw


def get_config() -> dict:
    """Get the add-on configuration."""
    return mw.addonManager.getConfig(__name__.split(".")[0]) or {}


def get_api_key() -> str:
    """Get the OpenAI API key from config."""
    config = get_config()
    return config.get("openai_api_key", "")


def get_tts_voice() -> str:
    """Get the TTS voice from config."""
    config = get_config()
    return config.get("tts_voice", "alloy")


def get_tts_model() -> str:
    """Get the TTS model from config."""
    config = get_config()
    return config.get("tts_model", "tts-1")


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
        A unique filename like 'saikou_abc123.mp3'
    """
    # Create a hash of the text for uniqueness
    text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{text_hash}.mp3"


def generate_audio(text: str, filename: Optional[str] = None) -> str:
    """
    Generate audio using OpenAI TTS and save to Anki media folder.

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
        raise ValueError("OpenAI API key not configured. Please set it in the add-on config.")

    if not filename:
        filename = generate_audio_filename(text)

    # Prepare the request
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": get_tts_model(),
        "input": text,
        "voice": get_tts_voice(),
        "response_format": "mp3",
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            audio_data = response.read()
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise Exception(f"OpenAI TTS API error ({e.code}): {error_body}")
    except urllib.error.URLError as e:
        raise Exception(f"Network error: {e.reason}")

    # Save to media folder
    media_path = os.path.join(get_media_folder(), filename)
    with open(media_path, "wb") as f:
        f.write(audio_data)

    # Register with Anki's media manager
    mw.col.media.add_file(media_path)

    return filename


def generate_word_audio(word: str) -> str:
    """
    Generate audio for a single word.

    Args:
        word: The word to generate audio for

    Returns:
        The sound tag string like '[sound:filename.mp3]'
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
        The sound tag string like '[sound:filename.mp3]'
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
