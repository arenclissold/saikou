# 採鉱 (Saikou)

**AI-Powered Japanese Vocabulary Card Creator for Anki**

_Mining the best example sentences for your Japanese learning journey_

---

## Overview

採鉱 (Saikou) is an Anki add-on that helps you create high-quality Japanese vocabulary cards with AI assistance. It automatically fetches definitions, generates or finds example sentences, provides translations, and creates audio files—all in one streamlined workflow.

### Features

- 🎯 **Smart Dictionary Lookup** - Real-time word definitions from Jisho.org
- 📚 **Example Sentences** - Automatically fetches real example sentences from Tatoeba, with Google Gemini AI fallback
- 🌐 **AI Translation** - Natural English translations powered by Google Gemini
- 🔊 **Audio Generation** - High-quality Japanese text-to-speech using Google Gemini TTS
- 🎨 **Flexible Field Mapping** - Works with your existing note types or create a default setup
- ⚡ **Async & Debounced** - Non-blocking UI with smart request throttling

---

## Installation

1. Download the add-on from the Anki add-on repository (or install manually)
2. Restart Anki
3. The **Saikou** menu will appear in Anki's menu bar (before the Help menu)

---

## Quick Start

### 1. Configure Your Google API Key

1. Get your API key from: https://aistudio.google.com/app/apikey
   - Enable the **Gemini API** for your project
2. In Anki, go to **Saikou → Settings**
3. Enter your Google API key in the "Google API Key" field
4. (Optional) Adjust other settings:
   - **Gemini Model**: Choose your preferred model (default: `gemini-2.5-flash`)
     - Options: `gemini-3-flash-preview`, `gemini-3-pro-preview`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-2.5-pro`
   - **TTS Model**: Text-to-speech model (default: `gemini-3.1-flash-tts-preview`)
     - Options: `gemini-3.1-flash-tts-preview`, `gemini-2.5-flash-tts`, `gemini-2.5-flash-lite-preview-tts`
   - **TTS Voice**: Select the voice for audio generation (default: `Kore`)
     - 30 voice options available including: `Zephyr`, `Puck`, `Charon`, `Kore`, `Fenrir`, `Leda`, `Orus`, `Aoede`, and more
5. Click **Save**

> **Note**: The Google API key is required for generating sentences, translations, and audio. Without it, you'll only be able to look up definitions.

### 2. Set Up Field Mappings

採鉱 needs to know which deck and note type to use, and how to map its fields to your note type's fields.

#### Option A: Use Default Setup (Recommended for New Users)

1. Go to **Saikou → Map Fields...**
2. Click **"Create Default Saikou Setup"**
3. This will automatically:
   - Create a "Saikou" deck
   - Create a "Saikou Japanese" note type with all required fields
   - Set up card templates with styling
   - Auto-map all fields

You're ready to go! Skip to [Creating Cards](#creating-cards).

#### Option B: Map to Your Existing Note Type

1. Go to **Saikou → Map Fields...**
2. Select your **Deck** from the dropdown
3. Select your **Note Type** from the dropdown
4. Map each 採鉱 field to a field in your note type:
   - **Target Word** (required) - The Japanese word you're learning
   - **Sentence** - Example sentence in Japanese
   - **Sentence Translation** - English translation of the sentence
   - **Definition** - Word definition
   - **Sentence Audio** - Audio file reference for the sentence
   - **Word Audio** - Audio file reference for the word
5. Fields will auto-map if your note type has matching field names
6. Click **Save**

> **Tip**: You can leave fields unmapped if you don't want to use them. Only "Target Word" is required.

---

## Creating Cards

1. Go to **Saikou → Create Card**
2. Enter a **Target Word** (Japanese word you want to learn)
3. Use the features:

   **Dictionary Search Panel (Left Side):**
   - Search for words to see definitions
   - Click a result to view details
   - Click **"Use This Word"** to populate the card creator

   **Card Creator (Right Side):**
   - **Generate All** - Automatically fills all empty fields
   - **Individual Generate Buttons** - Generate specific fields:
     - Definition (from Jisho)
     - Sentence (from Tatoeba, falls back to AI)
     - Translation (from Tatoeba or AI)
     - Audio (for sentence and word)

4. Review and edit the generated content
5. Click **Save Card** to add it to your deck

### Tips

- **Target Word** is always required
- The dictionary lookup is automatic and debounced (waits 300ms after you stop typing)
- Example sentences are fetched from Tatoeba first (real examples), then AI-generated if none found
- Audio files are saved to Anki's media folder and automatically linked

---

## How It Works

### Example Sentence Flow

1. **Tatoeba Search** - First, 採鉱 searches Tatoeba.org for real example sentences containing your target word
2. **AI Fallback** - If no Tatoeba results are found, it generates a sentence using Google Gemini
3. **Translation** - If Tatoeba provided the sentence, it includes the translation. Otherwise, Gemini generates one

### Dictionary Lookup

- Uses Jisho.org API for real-time word definitions
- Async and debounced to prevent UI blocking
- Shows kanji, readings, and English definitions

### Audio Generation

- Uses Google Gemini TTS models with advanced features:
  - Enhanced expressivity and natural speech
  - Precision pacing for better prosody
  - Multiple voice options including Kore, Zephyr, Puck, Charon, Fenrir, and Aoede
- Files are saved as WAV audio in Anki's media folder
- Automatically linked in your cards

---

## Troubleshooting

### "Google API key not configured" Warning

- Go to **Saikou → Settings** and enter your API key
- Get your key from https://aistudio.google.com/app/apikey
- Make sure the Gemini API is enabled (includes TTS capabilities)
- Click **Save**

### "No fields mapped" Error

- Go to **Saikou → Map Fields...** and configure your field mappings
- Make sure at least "Target Word" is mapped

### Menu Not Appearing

- Restart Anki completely
- Make sure the add-on is enabled in **Tools → Add-ons**

### Example Sentences Not Found

- This is normal! 採鉱 will automatically fall back to Google Gemini-generated sentences
- Tatoeba may not have examples for every word, especially rare or new vocabulary

---

## Configuration Reference

### Settings (Saikou → Settings)

| Setting        | Description                    | Default                        |
| -------------- | ------------------------------ | ------------------------------ |
| Google API Key | Your Google API key (required) | -                              |
| Gemini Model   | Model for text generation      | `gemini-2.5-flash`             |
| TTS Model      | Model for audio generation     | `gemini-3.1-flash-tts-preview` |
| TTS Voice      | Voice for audio generation     | `Kore`                         |

### Field Mappings (Saikou → Map Fields...)

Configure which deck and note type to use, and map 採鉱 fields to your note type fields.

---

## Requirements

- Anki 2.1.50 or later
- Google API key with Gemini API enabled (includes TTS)
- Internet connection (for dictionary lookups, Tatoeba searches, and AI features)

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

For issues, feature requests, or questions:

- [GitHub Issues](https://github.com/yourusername/saikou/issues)
- [Anki Add-on Page](https://ankiweb.net/shared/info/your-addon-id)

---

**Happy mining! 🎌**
