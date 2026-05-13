# Configuration dialog for Saikou

from aqt.qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
)

from ..utils import get_config, save_config

# Available options for dropdowns
GEMINI_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
]

TTS_MODELS = [
    "gemini-3.1-flash-tts-preview",
    "gemini-2.5-flash-tts",
    "gemini-2.5-flash-lite-preview-tts",
]

TTS_VOICES = [
    "Zephyr",
    "Puck",
    "Charon",
    "Kore",
    "Fenrir",
    "Leda",
    "Orus",
    "Aoede",
    "Callirrhoe",
    "Autonoe",
    "Enceladus",
    "Iapetus",
    "Umbriel",
    "Algieba",
    "Despina",
    "Erinome",
    "Algenib",
    "Rasalgethi",
    "Laomedeia",
    "Achernar",
    "Alnilam",
    "Schedar",
    "Gacrux",
    "Pulcherrima",
    "Achird",
    "Zubenelgenubi",
    "Vindemiatrix",
    "Sadachbia",
    "Sadaltager",
    "Sulafat",
]


class ConfigDialog(QDialog):
    """Configuration dialog with form elements."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Saikou Configuration")
        self.setMinimumWidth(450)

        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Form layout
        form_layout = QFormLayout()

        # Google API Key with Show/Hide button
        api_key_layout = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("AIza...")
        api_key_layout.addWidget(self.api_key_input)
        self.show_key_btn = QPushButton("Show")
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.toggled.connect(self._toggle_api_key_visibility)
        api_key_layout.addWidget(self.show_key_btn)
        form_layout.addRow("Google API Key:", api_key_layout)

        # Gemini Model
        self.model_combo = QComboBox()
        self.model_combo.addItems(GEMINI_MODELS)
        form_layout.addRow("Gemini Model:", self.model_combo)

        # TTS Model
        self.tts_model_combo = QComboBox()
        self.tts_model_combo.addItems(TTS_MODELS)
        form_layout.addRow("TTS Model:", self.tts_model_combo)

        # TTS Voice
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(TTS_VOICES)
        form_layout.addRow("TTS Voice:", self.voice_combo)

        layout.addLayout(form_layout)

        # Help text
        help_label = QLabel(
            '<small>Get your Google API key from: '
            '<a href="https://aistudio.google.com/app/apikey">aistudio.google.com/app/apikey</a></small>'
        )
        help_label.setOpenExternalLinks(True)
        layout.addWidget(help_label)

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

    def _toggle_api_key_visibility(self, checked: bool):
        """Toggle API key visibility."""
        if checked:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_key_btn.setText("Hide")
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_key_btn.setText("Show")

    def _load_config(self):
        """Load current configuration into form."""
        config = get_config()

        # API Key
        self.api_key_input.setText(config.get("google_api_key", ""))

        # Gemini Model
        model = config.get("gemini_model", "gemini-2.5-flash")
        index = self.model_combo.findText(model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)

        # TTS Model
        tts_model = config.get("tts_model", "gemini-3.1-flash-tts-preview")
        index = self.tts_model_combo.findText(tts_model)
        if index >= 0:
            self.tts_model_combo.setCurrentIndex(index)

        # TTS Voice
        voice = config.get("tts_voice", "Kore")
        index = self.voice_combo.findText(voice)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)

    def _save_and_close(self):
        """Save configuration and close dialog."""
        config = get_config()
        config.update({
            "google_api_key": self.api_key_input.text().strip(),
            "gemini_model": self.model_combo.currentText(),
            "tts_model": self.tts_model_combo.currentText(),
            "tts_voice": self.voice_combo.currentText(),
        })

        save_config(config)
        self.accept()
