# Field mapping dialog for Saikou

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


def get_config() -> dict:
    """Get the current configuration."""
    return mw.addonManager.getConfig(get_addon_name()) or {}


def save_config(config: dict):
    """Save the configuration."""
    mw.addonManager.writeConfig(get_addon_name(), config)


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
        QMessageBox.information(self, "Success", "Field mappings saved!")
        self.accept()
