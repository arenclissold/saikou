# OpenAI client for text generation

from typing import Optional, Tuple
import json

from aqt import mw
from .tatoeba import get_example_sentence


def get_config() -> dict:
    """Get the add-on configuration."""
    return mw.addonManager.getConfig(__name__.split(".")[0]) or {}


def get_api_key() -> str:
    """Get the OpenAI API key from config."""
    config = get_config()
    return config.get("openai_api_key", "")


def get_model() -> str:
    """Get the OpenAI model from config."""
    config = get_config()
    return config.get("openai_model", "gpt-4o-mini")


def _make_request(endpoint: str, payload: dict) -> dict:
    """
    Make a request to the OpenAI API.

    Args:
        endpoint: The API endpoint (e.g., 'chat/completions')
        payload: The request payload

    Returns:
        The JSON response

    Raises:
        Exception: If the request fails
    """
    import urllib.request
    import urllib.error

    api_key = get_api_key()
    if not api_key:
        raise ValueError("OpenAI API key not configured. Please set it in the add-on config.")

    url = f"https://api.openai.com/v1/{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise Exception(f"OpenAI API error ({e.code}): {error_body}")
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

    payload = {
        "model": get_model(),
        "messages": [
            {"role": "system", "content": "You are a Japanese language teacher helping students learn vocabulary through example sentences."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 200,
    }

    response = _make_request("chat/completions", payload)
    return response["choices"][0]["message"]["content"].strip()


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

    payload = {
        "model": get_model(),
        "messages": [
            {"role": "system", "content": "You are a professional Japanese-English translator. Provide accurate, natural translations."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 200,
    }

    response = _make_request("chat/completions", payload)
    return response["choices"][0]["message"]["content"].strip()


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

    payload = {
        "model": get_model(),
        "messages": [
            {"role": "system", "content": "You are a Japanese language teacher. Generate example sentences and translations."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 300,
    }

    response = _make_request("chat/completions", payload)
    content = response["choices"][0]["message"]["content"].strip()

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
