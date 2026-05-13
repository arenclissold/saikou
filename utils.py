# Utility functions for Saikou

import copy
import json
from pathlib import Path


CONFIG_FILENAME = "config.json"
DEFAULT_CONFIG_FILENAME = "default_config.json"

FALLBACK_DEFAULT_CONFIG = {
    "google_api_key": "",
    "gemini_model": "gemini-2.5-flash",
    "tts_model": "gemini-2.5-flash-preview-tts",
    "tts_voice": "Kore",
    "field_mapping": {
        "deck_id": None,
        "deck_name": "",
        "notetype_id": None,
        "notetype_name": "",
        "mappings": {},
    },
}


def get_addon_dir() -> Path:
    """Return the add-on directory."""
    return Path(__file__).resolve().parent


def _load_json_file(path: Path) -> dict:
    """Load a JSON object from disk."""
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        print(f"Error loading {path.name}: {e}")
        return {}

    if not isinstance(data, dict):
        print(f"Error loading {path.name}: expected a JSON object")
        return {}

    return data


def _merge_config(defaults: dict, overrides: dict) -> dict:
    """Recursively merge user config over default config."""
    merged = copy.deepcopy(defaults)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_config(merged[key], value)
        else:
            merged[key] = value
    return merged


def get_default_config() -> dict:
    """Load the tracked default configuration."""
    default_path = get_addon_dir() / DEFAULT_CONFIG_FILENAME
    defaults = _load_json_file(default_path)
    if not defaults:
        defaults = FALLBACK_DEFAULT_CONFIG
    return copy.deepcopy(defaults)


def get_config_path() -> Path:
    """Return the local configuration path."""
    return get_addon_dir() / CONFIG_FILENAME


def get_config() -> dict:
    """Load local config merged over tracked defaults."""
    defaults = get_default_config()
    config_path = get_config_path()
    if not config_path.exists():
        try:
            save_config(defaults)
        except OSError as e:
            print(f"Error creating {CONFIG_FILENAME}: {e}")
        return defaults

    local_config = _load_json_file(config_path)
    return _merge_config(defaults, local_config)


def save_config(config: dict) -> None:
    """Save the local configuration used by the add-on."""
    config_path = get_config_path()
    config_to_save = _merge_config(get_default_config(), config)
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config_to_save, f, ensure_ascii=False, indent=2)
        f.write("\n")
