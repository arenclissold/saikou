# Dictionary lookup service using Jisho API

import json
import urllib.request
import urllib.error
from typing import Dict, List, Optional

# Jisho API endpoint
JISHO_API_URL = "https://jisho.org/api/v1/search/words"


def lookup_word(word: str) -> Optional[str]:
    """
    Look up a word using the Jisho API and return its definition.

    Args:
        word: The Japanese word to look up (kanji or reading)

    Returns:
        A formatted string with definitions, or None if not found
    """
    try:
        # Build the API URL
        encoded_word = urllib.request.quote(word)
        url = f"{JISHO_API_URL}?keyword={encoded_word}"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Saikou-Anki-Addon/1.0"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        if not data.get("data"):
            return None

        # Find the best match (exact match preferred)
        best_entry = None
        for entry in data["data"]:
            japanese = entry.get("japanese", [])
            for jp in japanese:
                if jp.get("word") == word or jp.get("reading") == word:
                    best_entry = entry
                    break
            if best_entry:
                break

        # If no exact match, use the first result
        if not best_entry:
            best_entry = data["data"][0]

        return format_jisho_entry(best_entry)

    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return None
    except Exception:
        return None


def get_word_details(word: str) -> Optional[Dict]:
    """
    Get full word details from Jisho API.

    Args:
        word: The Japanese word to look up

    Returns:
        Dictionary with word details or None if not found
    """
    try:
        encoded_word = urllib.request.quote(word)
        url = f"{JISHO_API_URL}?keyword={encoded_word}"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Saikou-Anki-Addon/1.0"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        if not data.get("data"):
            return None

        # Find the best match (exact match preferred)
        best_entry = None
        for entry in data["data"]:
            japanese = entry.get("japanese", [])
            for jp in japanese:
                if jp.get("word") == word or jp.get("reading") == word:
                    best_entry = entry
                    break
            if best_entry:
                break

        # If no exact match, use the first result
        if not best_entry:
            best_entry = data["data"][0]

        # Extract word details
        japanese = best_entry.get("japanese", [{}])[0]
        word_text = japanese.get("word") or japanese.get("reading", "")
        reading = japanese.get("reading", "")

        return {
            "word": word_text,
            "reading": reading,
            "definition": format_jisho_entry(best_entry),
            "full_entry": best_entry
        }

    except Exception:
        return None


def format_jisho_entry(entry: dict) -> str:
    """
    Format a Jisho API entry into a readable definition string.

    Args:
        entry: The Jisho API entry dictionary

    Returns:
        A formatted definition string
    """
    definitions = []

    senses = entry.get("senses", [])
    for i, sense in enumerate(senses, 1):
        # Get English definitions
        english_defs = sense.get("english_definitions", [])
        if not english_defs:
            continue

        # Get parts of speech
        pos = sense.get("parts_of_speech", [])
        pos_str = f"({', '.join(pos)}) " if pos else ""

        # Format the definition
        def_text = "; ".join(english_defs)
        definitions.append(f"{i}. {pos_str}{def_text}")

    return "\n".join(definitions) if definitions else None


def search_words(query: str, limit: int = 10) -> List[Dict]:
    """
    Search for words matching a query using Jisho API.

    Args:
        query: The search query
        limit: Maximum number of results

    Returns:
        List of matching entries with word and definition
    """
    results = []

    try:
        encoded_query = urllib.request.quote(query)
        url = f"{JISHO_API_URL}?keyword={encoded_query}"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Saikou-Anki-Addon/1.0"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        for entry in data.get("data", [])[:limit]:
            japanese = entry.get("japanese", [{}])[0]
            word_text = japanese.get("word") or japanese.get("reading", "")

            if word_text:
                results.append({
                    "word": word_text,
                    "reading": japanese.get("reading", ""),
                    "definition": format_jisho_entry(entry)
                })

    except Exception:
        pass

    return results
