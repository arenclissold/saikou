# Field mapping dialog for Saikou

import os
from pathlib import Path

from aqt.qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QMessageBox,
)
from aqt import mw

from ..utils import get_config, save_config


# Saikou fields that need to be mapped
SAIKOU_FIELDS = [
    ("target_word", "Target Word"),
    ("sentence", "Sentence"),
    ("sentence_translation", "Sentence Translation"),
    ("definition", "Definition"),
    ("sentence_audio", "Sentence Audio"),
    ("word_audio", "Word Audio"),
]

# Auto-mapping aliases: lowercase variations that should match each Saikou field
FIELD_ALIASES = {
    "target_word": ["target word", "targetword", "word", "vocabulary", "vocab", "term", "expression"],
    "sentence": ["sentence", "example", "example sentence", "examplesentence", "context"],
    "sentence_translation": ["sentence translation", "sentencetranslation", "translation", "meaning", "english"],
    "definition": ["definition", "definitions", "meaning", "meanings", "gloss"],
    "sentence_audio": ["sentence audio", "sentenceaudio", "audio sentence", "example audio"],
    "word_audio": ["word audio", "wordaudio", "audio", "pronunciation", "reading audio"],
}


def get_addon_name() -> str:
    """Get the add-on folder name."""
    return __name__.split(".")[0]


def _get_template_path(filename: str) -> str:
    """Get the path to a template file as a string."""
    # Get addon path - try addonManager first, then fallback to relative path
    try:
        addon_name = get_addon_name()
        # Try to get addons folder - it might be a property or method
        addons_folder = mw.addonManager.addonsFolder
        if callable(addons_folder):
            addons_folder = addons_folder()
        addon_path = Path(str(addons_folder)) / addon_name
        template_path = addon_path / "templates" / filename
        if template_path.exists():
            return str(template_path)
    except (AttributeError, KeyError, TypeError):
        pass

    # Fallback to relative path from this file (for development/testing)
    addon_path = Path(__file__).parent.parent
    template_path = addon_path / "templates" / filename
    return str(template_path)


def _read_template_file(filename: str) -> str:
    """Read a template file and return its contents."""
    template_path = _get_template_path(filename)
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to empty string if file doesn't exist
        return ""


class FieldMappingDialog(QDialog):
    """Dialog for mapping Saikou fields to note type fields."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Saikou - Map Fields")
        self.setMinimumWidth(500)

        self._field_combos = {}
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Instructions
        info_label = QLabel(
            "Select the deck and note type to use, then map each Saikou field\n"
            "to a field in your note type. Leave empty to skip a field."
        )
        layout.addWidget(info_label)

        # Create default setup button (smaller, secondary style)
        create_default_btn = QPushButton("Create Default Saikou Setup")
        create_default_btn.clicked.connect(self._create_default_setup)
        create_default_btn.setMaximumWidth(200)
        layout.addWidget(create_default_btn)

        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Deck selector
        self.deck_combo = QComboBox()
        self._populate_decks()
        form_layout.addRow("Deck", self.deck_combo)

        # Note type selector
        self.notetype_combo = QComboBox()
        self._populate_notetypes()
        self.notetype_combo.currentIndexChanged.connect(self._on_notetype_changed)
        form_layout.addRow("Note Type", self.notetype_combo)

        layout.addLayout(form_layout)

        # Separator
        separator_label = QLabel("Field Mappings")
        separator_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(separator_label)

        # Field mappings
        self.field_form_layout = QFormLayout()
        self.field_form_layout.setSpacing(8)

        for field_key, field_label in SAIKOU_FIELDS:
            combo = QComboBox()
            combo.addItem("(none)", "")
            self._field_combos[field_key] = combo
            self.field_form_layout.addRow(field_label, combo)

        layout.addLayout(self.field_form_layout)

        # Populate field combos with current note type fields
        self._update_field_combos()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save_and_close)
        button_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def _populate_decks(self):
        """Populate the deck dropdown."""
        self.deck_combo.clear()
        decks = mw.col.decks.all_names_and_ids()
        for deck in decks:
            self.deck_combo.addItem(deck.name, deck.id)

    def _populate_notetypes(self):
        """Populate the note type dropdown."""
        self.notetype_combo.clear()
        models = mw.col.models.all_names_and_ids()
        for model in models:
            self.notetype_combo.addItem(model.name, model.id)

    def _on_notetype_changed(self):
        """Handle note type selection change."""
        # Auto-map fields when user changes note type
        self._update_field_combos(auto_map=True)

    def _update_field_combos(self, auto_map: bool = True):
        """Update field combo boxes with fields from selected note type."""
        notetype_id = self.notetype_combo.currentData()
        if not notetype_id:
            return

        model = mw.col.models.get(notetype_id)
        if not model:
            return

        field_names = [field["name"] for field in model["flds"]]

        for field_key, combo in self._field_combos.items():
            current_value = combo.currentData()
            combo.clear()
            combo.addItem("(none)", "")
            for field_name in field_names:
                combo.addItem(field_name, field_name)

            # Restore selection if field still exists
            if current_value:
                index = combo.findData(current_value)
                if index >= 0:
                    combo.setCurrentIndex(index)
                    continue

            # Auto-map if no current selection and auto_map is enabled
            if auto_map and not current_value:
                self._try_auto_map(field_key, combo, field_names)

    def _try_auto_map(self, field_key: str, combo: QComboBox, field_names: list):
        """Try to auto-map a Saikou field to a note type field by name matching."""
        aliases = FIELD_ALIASES.get(field_key, [])

        for field_name in field_names:
            # Normalize field name for comparison
            normalized = field_name.lower().strip()

            # Check if it matches any alias
            if normalized in aliases:
                index = combo.findData(field_name)
                if index >= 0:
                    combo.setCurrentIndex(index)
                    return

    def _load_config(self):
        """Load current configuration into form."""
        config = get_config()
        field_mapping = config.get("field_mapping", {})

        # Deck
        deck_id = field_mapping.get("deck_id")
        if deck_id:
            index = self.deck_combo.findData(deck_id)
            if index >= 0:
                self.deck_combo.setCurrentIndex(index)

        # Note type
        notetype_id = field_mapping.get("notetype_id")
        has_saved_mappings = bool(field_mapping.get("mappings"))

        if notetype_id:
            index = self.notetype_combo.findData(notetype_id)
            if index >= 0:
                self.notetype_combo.setCurrentIndex(index)
                # Don't auto-map if we have saved mappings
                self._update_field_combos(auto_map=not has_saved_mappings)

        # Load saved field mappings
        mappings = field_mapping.get("mappings", {})
        for field_key, combo in self._field_combos.items():
            mapped_field = mappings.get(field_key, "")
            if mapped_field:
                index = combo.findData(mapped_field)
                if index >= 0:
                    combo.setCurrentIndex(index)

    def _save_and_close(self):
        """Save configuration and close dialog."""
        # Validate that at least target_word is mapped
        target_word_mapping = self._field_combos["target_word"].currentData()
        if not target_word_mapping:
            QMessageBox.warning(
                self,
                "Warning",
                "Please map at least the Target Word field."
            )
            return

        config = get_config()

        # Build field mapping config
        mappings = {}
        for field_key, combo in self._field_combos.items():
            value = combo.currentData()
            if value:
                mappings[field_key] = value

        config["field_mapping"] = {
            "deck_id": self.deck_combo.currentData(),
            "deck_name": self.deck_combo.currentText(),
            "notetype_id": self.notetype_combo.currentData(),
            "notetype_name": self.notetype_combo.currentText(),
            "mappings": mappings,
        }

        save_config(config)
        self.accept()

    def _create_default_setup(self):
        """Create default Saikou deck, note type, and card templates."""
        reply = QMessageBox.question(
            self,
            "Create Default Setup",
            "This will create:\n"
            "- A deck named 'Saikou'\n"
            "- A note type named 'Saikou Japanese' with all required fields\n"
            "- Card templates\n"
            "- Auto-configured field mappings\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # 1. Create deck
            deck_id = self._create_default_deck()
            if not deck_id:
                QMessageBox.critical(self, "Error", "Failed to create deck.")
                return

            # 2. Create note type
            notetype_id = self._create_default_notetype()
            if not notetype_id:
                QMessageBox.critical(self, "Error", "Failed to create note type.")
                return

            # 3. Auto-map fields
            self._auto_map_default_fields(deck_id, notetype_id)

            # 4. Refresh UI and reload mappings
            self._populate_decks()
            self._populate_notetypes()
            self.deck_combo.setCurrentIndex(self.deck_combo.findData(deck_id))
            self.notetype_combo.setCurrentIndex(self.notetype_combo.findData(notetype_id))
            self._update_field_combos(auto_map=False)
            # Reload config to populate field mappings
            self._load_config()

            QMessageBox.information(
                self,
                "Success",
                "Default Saikou setup created successfully!\n\n"
                "Deck: Saikou\n"
                "Note Type: Saikou Japanese\n"
                "All fields have been auto-mapped."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create default setup:\n{str(e)}")

    def _create_default_deck(self):
        """Create the default Saikou deck."""
        deck_name = "Saikou"

        # Check if deck already exists
        decks = mw.col.decks.all_names_and_ids()
        for deck in decks:
            if deck.name == deck_name:
                return deck.id

        # Create new deck
        deck_id = mw.col.decks.id(deck_name)
        mw.col.decks.save(mw.col.decks.get(deck_id))
        mw.col.decks.flush()

        return deck_id

    def _create_default_notetype(self):
        """Create the default Saikou note type with fields and templates."""
        notetype_name = "Saikou Japanese"

        # Check if note type already exists
        models = mw.col.models.all_names_and_ids()
        for model in models:
            if model.name == notetype_name:
                return model.id

        # Create new model
        mm = mw.col.models
        model = mm.new(notetype_name)

        # Add fields
        field_names = [
            "Target Word",
            "Sentence",
            "Sentence Translation",
            "Definition",
            "Sentence Audio",
            "Word Audio",
        ]

        for field_name in field_names:
            field = mm.new_field(field_name)
            mm.add_field(model, field)

        # Create card template
        template = mm.new_template("Card 1")

        # Load templates from files
        front_template = _read_template_file("card_front.html")
        back_template = _read_template_file("card_back.html")
        css_styling = _read_template_file("card.css")

        # Set templates
        template["qfmt"] = front_template
        template["afmt"] = back_template

        mm.add_template(model, template)

        # Add CSS styling
        model["css"] = css_styling

        # Save model
        mm.save(model)
        mw.col.models.flush()

        return model["id"]

    def _auto_map_default_fields(self, deck_id, notetype_id):
        """Auto-map all fields for the default setup."""
        model = mw.col.models.get(notetype_id)
        if not model:
            return

        # Build mappings - all fields map to themselves
        mappings = {
            "target_word": "Target Word",
            "sentence": "Sentence",
            "sentence_translation": "Sentence Translation",
            "definition": "Definition",
            "sentence_audio": "Sentence Audio",
            "word_audio": "Word Audio",
        }

        # Get deck name
        deck = mw.col.decks.get(deck_id)
        deck_name = deck["name"] if deck else "Saikou"

        # Save configuration
        config = get_config()
        config["field_mapping"] = {
            "deck_id": deck_id,
            "deck_name": deck_name,
            "notetype_id": notetype_id,
            "notetype_name": model["name"],
            "mappings": mappings,
        }
        save_config(config)
