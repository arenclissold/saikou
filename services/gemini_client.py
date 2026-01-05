# Google Gemini client for text generation

from typing import Optional, Tuple
import json
import os

from aqt import mw
from .tatoeba import get_example_sentence


def get_config() -> dict:
    """Get the add-on configuration."""
    return mw.addonManager.getConfig(__name__.split(".")[0]) or {}


def get_api_key() -> str:
    """
    Get the Google API key from environment variable or config.
    Priority: GOOGLE_API_KEY env var > config.json
    """
    # First try environment variable
    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if api_key:
        return api_key

    # Fall back to config.json
    config = get_config()
    return config.get("google_api_key", "")


def get_model() -> str:
    """Get the Gemini model from config."""
    config = get_config()
    return config.get("gemini_model", "gemini-2.5-flash")


def _make_request(prompt: str, system_instruction: Optional[str] = None, temperature: float = 0.7) -> str:
    """
    Make a request to the Google Gemini API.

    Args:
        prompt: The user prompt
        system_instruction: Optional system instruction
        temperature: Temperature for generation (0.0 to 2.0)

    Returns:
        The generated text response

    Raises:
        Exception: If the request fails
    """
    import urllib.request
    import urllib.error

    api_key = get_api_key()
    if not api_key:
        raise ValueError("Google API key not configured. Please set it in the add-on config.")

    model = get_model()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    headers = {
        "Content-Type": "application/json",
    }

    # Build the request payload
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 1000,
        }
    }

    # Add system instruction if provided
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{
                "text": system_instruction
            }]
        }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))

        # Extract the text from the response
        if "candidates" in result and len(result["candidates"]) > 0:
            candidate = result["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                parts = candidate["content"]["parts"]
                if len(parts) > 0 and "text" in parts[0]:
                    return parts[0]["text"].strip()

        raise Exception("Unexpected response format from Gemini API")

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise Exception(f"Google Gemini API error ({e.code}): {error_body}")
    except urllib.error.URLError as e:
        raise Exception(f"Network error: {e.reason}")


def generate_sentence(word: str, definition: Optional[str] = None) -> str:
    """
    Generate an example sentence containing the target word.

    Args:
        word: The Japanese word to use in the sentence
        definition: Optional definition to help with context

    Returns:
        A Japanese sentence containing the word
    """
    context = f" (meaning: {definition})" if definition else ""

    prompt = f"""Generate a natural, everyday Japanese sentence using the word "{word}"{context}.

Requirements:
- The sentence should be appropriate for language learners
- Use natural, conversational Japanese
- Keep the sentence relatively simple but meaningful
- Only output the Japanese sentence, nothing else"""

    system_instruction = "You are a Japanese language teacher helping students learn vocabulary through example sentences."

    return _make_request(prompt, system_instruction, temperature=0.7)


def translate_sentence(sentence: str) -> str:
    """
    Translate a Japanese sentence to English.

    Args:
        sentence: The Japanese sentence to translate

    Returns:
        The English translation
    """
    prompt = f"""Translate the following Japanese sentence to English:

{sentence}

Provide only the translation, nothing else."""

    system_instruction = "You are a professional Japanese-English translator. Provide accurate, natural translations."

    return _make_request(prompt, system_instruction, temperature=0.3)


def generate_and_translate(word: str, definition: Optional[str] = None) -> Tuple[str, str]:
    """
    Generate a sentence and translate it in one call for efficiency.
    Tries Tatoeba first, then falls back to AI if no examples found.

    Args:
        word: The Japanese word to use
        definition: Optional definition for context

    Returns:
        Tuple of (Japanese sentence, English translation)
    """
    # Try Tatoeba first
    tatoeba_result = get_example_sentence(word)
    if tatoeba_result:
        return tatoeba_result

    # Fall back to AI generation
    context = f" (meaning: {definition})" if definition else ""

    prompt = f"""Generate a natural Japanese sentence using the word "{word}"{context}, then translate it to English.

Requirements:
- The sentence should be appropriate for language learners
- Use natural, conversational Japanese
- Keep the sentence relatively simple but meaningful

Output format (exactly two lines):
Japanese: [sentence]
English: [translation]"""

    system_instruction = "You are a Japanese language teacher. Generate example sentences and translations."

    content = _make_request(prompt, system_instruction, temperature=0.7)

    # Parse the response
    lines = content.split("\n")
    sentence = ""
    translation = ""

    for line in lines:
        line = line.strip()
        if line.lower().startswith("japanese:"):
            sentence = line.split(":", 1)[1].strip()
        elif line.lower().startswith("english:"):
            translation = line.split(":", 1)[1].strip()

    # Fallback if parsing fails
    if not sentence and len(lines) >= 1:
        sentence = lines[0].replace("Japanese:", "").strip()
    if not translation and len(lines) >= 2:
        translation = lines[1].replace("English:", "").strip()

    return sentence, translation


def get_sentence_with_fallback(word: str, definition: Optional[str] = None) -> str:
    """
    Get an example sentence, trying Tatoeba first, then falling back to AI.

    Args:
        word: The Japanese word to use
        definition: Optional definition for context

    Returns:
        A Japanese sentence containing the word
    """
    # Try Tatoeba first
    tatoeba_result = get_example_sentence(word)
    if tatoeba_result:
        return tatoeba_result[0]  # Return just the Japanese sentence

    # Fall back to AI generation
    return generate_sentence(word, definition)
