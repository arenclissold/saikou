# Tatoeba API client for example sentences

import json
import urllib.request
import urllib.error
from typing import Optional, Tuple, List, Dict


TATOEBA_API_URL = "https://api.tatoeba.org"


def search_sentences(word: str, limit: int = 5) -> List[Dict]:
    """
    Search for example sentences containing the word from Tatoeba.

    Args:
        word: The Japanese word to search for
        limit: Maximum number of results to return

    Returns:
        List of dictionaries with 'japanese' and 'english' keys, or empty list if none found
    """
    try:
        # Tatoeba API endpoint for searching sentences
        # from=jpn (Japanese), to=eng (English), query=word
        encoded_word = urllib.request.quote(word)
        # Search for Japanese sentences containing the word
        url = f"{TATOEBA_API_URL}/sentences/search?query={encoded_word}&from=jpn&to=eng&trans_filter=limit&trans_to=eng&sort=relevance"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Saikou-Anki-Addon/1.0"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        results = []

        # Tatoeba API can return data in different formats
        # Try to handle both array format and object with "data" key
        entries = []
        if isinstance(data, list):
            entries = data
        elif isinstance(data, dict):
            entries = data.get("data", [])

        if not entries:
            return []

        for entry in entries[:limit]:
            # Handle different response structures
            japanese_text = entry.get("text", "").strip()
            if not japanese_text:
                # Try alternative field names
                japanese_text = entry.get("sentence", {}).get("text", "").strip()

            # Get translations - could be in different formats
            translations = entry.get("translations", [])
            if not translations and "translation" in entry:
                translations = [entry["translation"]]

            # Find English translation
            english_text = ""
            for trans in translations:
                if isinstance(trans, dict):
                    if trans.get("lang") == "eng" or trans.get("language") == "eng":
                        english_text = trans.get("text", "").strip()
                        if not english_text:
                            english_text = trans.get("sentence", {}).get("text", "").strip()
                elif isinstance(trans, str):
                    # Sometimes translations are just strings
                    english_text = trans.strip()

                if english_text:
                    break

            if japanese_text and english_text:
                results.append({
                    "japanese": japanese_text,
                    "english": english_text
                })

        return results

    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError):
        return []
    except Exception:
        return []


def get_example_sentence(word: str) -> Optional[Tuple[str, str]]:
    """
    Get a single example sentence and translation from Tatoeba.

    Args:
        word: The Japanese word to search for

    Returns:
        Tuple of (Japanese sentence, English translation) or None if not found
    """
    sentences = search_sentences(word, limit=1)

    if sentences:
        sentence = sentences[0]
        return (sentence["japanese"], sentence["english"])

    return None
