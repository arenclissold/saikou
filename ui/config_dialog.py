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
    QMessageBox,
)
from aqt import mw


# Available options for dropdowns
OPENAI_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
]

TTS_VOICES = [
    "alloy",
    "echo",
    "fable",
    "onyx",
    "nova",
    "shimmer",
]

TTS_MODELS = [
    "tts-1",
    "tts-1-hd",
]

LANGUAGES = [
    "Japanese",
    "Chinese",
    "Korean",
    "Spanish",
    "French",
    "German",
    "Italian",
    "Portuguese",
    "Russian",
]

NATIVE_LANGUAGES = [
    "English",
    "Spanish",
    "French",
    "German",
    "Chinese",
    "Japanese",
    "Korean",
    "Portuguese",
    "Russian",
]


def get_addon_name() -> str:
    """Get the add-on folder name."""
    return __name__.split(".")[0]


def get_config() -> dict:
    """Get the current configuration."""
    return mw.addonManager.getConfig(get_addon_name()) or {}


def save_config(config: dict):
    """Save the configuration."""
    mw.addonManager.writeConfig(get_addon_name(), config)


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

        # OpenAI API Key with Show/Hide button
        api_key_layout = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        api_key_layout.addWidget(self.api_key_input)
        self.show_key_btn = QPushButton("Show")
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.toggled.connect(self._toggle_api_key_visibility)
        api_key_layout.addWidget(self.show_key_btn)
        form_layout.addRow("OpenAI API Key:", api_key_layout)

        # OpenAI Model
        self.model_combo = QComboBox()
        self.model_combo.addItems(OPENAI_MODELS)
        form_layout.addRow("OpenAI Model:", self.model_combo)

        # TTS Voice
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(TTS_VOICES)
        form_layout.addRow("TTS Voice:", self.voice_combo)

        # TTS Model
        self.tts_model_combo = QComboBox()
        self.tts_model_combo.addItems(TTS_MODELS)
        form_layout.addRow("TTS Model:", self.tts_model_combo)

        # Target Language
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(LANGUAGES)
        self.target_lang_combo.setEditable(True)
        form_layout.addRow("Target Language:", self.target_lang_combo)

        # Native Language
        self.native_lang_combo = QComboBox()
        self.native_lang_combo.addItems(NATIVE_LANGUAGES)
        self.native_lang_combo.setEditable(True)
        form_layout.addRow("Native Language:", self.native_lang_combo)

        layout.addLayout(form_layout)

        # Help text
        help_label = QLabel(
            '<small>Get your OpenAI API key from: '
            '<a href="https://platform.openai.com/api-keys">platform.openai.com/api-keys</a></small>'
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
        self.api_key_input.setText(config.get("openai_api_key", ""))

        # OpenAI Model
        model = config.get("openai_model", "gpt-4o-mini")
        index = self.model_combo.findText(model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)

        # TTS Voice
        voice = config.get("tts_voice", "alloy")
        index = self.voice_combo.findText(voice)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)

        # TTS Model
        tts_model = config.get("tts_model", "tts-1")
        index = self.tts_model_combo.findText(tts_model)
        if index >= 0:
            self.tts_model_combo.setCurrentIndex(index)

        # Target Language
        target_lang = config.get("target_language", "Japanese")
        index = self.target_lang_combo.findText(target_lang)
        if index >= 0:
            self.target_lang_combo.setCurrentIndex(index)
        else:
            self.target_lang_combo.setEditText(target_lang)

        # Native Language
        native_lang = config.get("native_language", "English")
        index = self.native_lang_combo.findText(native_lang)
        if index >= 0:
            self.native_lang_combo.setCurrentIndex(index)
        else:
            self.native_lang_combo.setEditText(native_lang)

    def _save_and_close(self):
        """Save configuration and close dialog."""
        config = {
            "openai_api_key": self.api_key_input.text().strip(),
            "openai_model": self.model_combo.currentText(),
            "tts_voice": self.voice_combo.currentText(),
            "tts_model": self.tts_model_combo.currentText(),
            "target_language": self.target_lang_combo.currentText(),
            "native_language": self.native_lang_combo.currentText(),
        }

        save_config(config)
        QMessageBox.information(self, "Success", "Configuration saved!")
        self.accept()
