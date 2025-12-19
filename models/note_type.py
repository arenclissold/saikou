# Note type management for Saikou

from typing import Optional

from anki.models import NotetypeDict
from aqt import mw

NOTE_TYPE_NAME = "Saikou Japanese"

FIELDS = [
    "TargetWord",
    "Sentence",
    "SentenceTranslation",
    "Definition",
    "SentenceAudio",
    "WordAudio",
]

FRONT_TEMPLATE = """<div class="word">{{TargetWord}}</div>
{{WordAudio}}
"""

BACK_TEMPLATE = """{{FrontSide}}

<hr id="answer">

<div class="definition">{{Definition}}</div>

<div class="sentence">{{Sentence}}</div>
{{SentenceAudio}}

<div class="translation">{{SentenceTranslation}}</div>
"""

CSS = """
.card {
    font-family: "Hiragino Kaku Gothic Pro", "Meiryo", "MS Gothic", sans-serif;
    font-size: 24px;
    text-align: center;
    color: black;
    background-color: white;
}

.word {
    font-size: 48px;
    font-weight: bold;
    margin: 20px 0;
}

.definition {
    font-size: 20px;
    margin: 15px 0;
    color: #333;
}

.sentence {
    font-size: 22px;
    margin: 15px 0;
}

.translation {
    font-size: 18px;
    margin: 15px 0;
    color: #666;
    font-style: italic;
}
"""


def get_or_create_note_type() -> NotetypeDict:
    """Get existing or create new Saikou Japanese note type."""
    model = mw.col.models.by_name(NOTE_TYPE_NAME)

    if model is None:
        model = create_note_type()

    return model


def create_note_type() -> NotetypeDict:
    """Create the Saikou Japanese note type."""
    model = mw.col.models.new(NOTE_TYPE_NAME)

    # Add fields
    for field_name in FIELDS:
        field = mw.col.models.new_field(field_name)
        mw.col.models.add_field(model, field)

    # Add card template
    template = mw.col.models.new_template("Card 1")
    template["qfmt"] = FRONT_TEMPLATE
    template["afmt"] = BACK_TEMPLATE
    mw.col.models.add_template(model, template)

    # Set CSS
    model["css"] = CSS

    # Save the model
    mw.col.models.add(model)

    return model


def get_note_type_id() -> Optional[int]:
    """Get the ID of the Saikou Japanese note type."""
    model = mw.col.models.by_name(NOTE_TYPE_NAME)
    if model:
        return model["id"]
    return None
