# Saikou Configuration

## Settings

### openai_api_key

Your OpenAI API key. Required for generating sentences, translations, and audio.
Get your API key from: https://platform.openai.com/api-keys

### openai_model

The OpenAI model to use for text generation.
Default: `gpt-4o-mini`
Options: `gpt-4o-mini`, `gpt-4o`, `gpt-3.5-turbo`

### tts_voice

The voice to use for text-to-speech audio generation.
Default: `alloy`
Options: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`

### tts_model

The TTS model to use for audio generation.
Default: `tts-1`
Options: `tts-1`, `tts-1-hd`

### target_language

The language you are learning.
Default: `Japanese`

### native_language

Your native language for translations.
Default: `English`

### field_mapping

Maps Saikou fields to fields in your chosen note type. Configure this through:
**Tools → Saikou → Map Fields...**

This allows you to:

- Select which deck cards will be added to
- Select which note type to use
- Map each Saikou field (Target Word, Sentence, Translation, Definition, Sentence Audio, Word Audio) to a field in your note type
