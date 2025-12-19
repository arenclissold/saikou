# Card creator dialog for Saikou

from aqt.qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QMessageBox,
    QProgressDialog,
    Qt,
)
from aqt import mw
from anki.notes import Note

from ..models.note_type import get_or_create_note_type, FIELDS
from ..services.jmdict import lookup_word
from ..services.openai_client import generate_sentence, translate_sentence
from ..services.audio import generate_word_audio, generate_sentence_audio


class CardCreatorDialog(QDialog):
    """Dialog for creating Japanese vocabulary cards with AI assistance."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Saikou - Create Japanese Card")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI using standard widgets."""
        layout = QVBoxLayout(self)

        # Form layout for fields
        form_layout = QFormLayout()

        # Target Word (required)
        word_layout = QHBoxLayout()
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("The word you want to learn")
        self.word_input.textChanged.connect(self._on_word_changed)
        word_layout.addWidget(self.word_input)
        form_layout.addRow("Target Word *:", word_layout)

        # Sentence
        sentence_layout = QHBoxLayout()
        self.sentence_input = QTextEdit()
        self.sentence_input.setPlaceholderText("Example sentence (will be generated if empty)")
        self.sentence_input.setMaximumHeight(60)
        sentence_layout.addWidget(self.sentence_input)
        self.generate_sentence_btn = QPushButton("Generate")
        self.generate_sentence_btn.clicked.connect(self._generate_sentence)
        sentence_layout.addWidget(self.generate_sentence_btn)
        form_layout.addRow("Sentence:", sentence_layout)

        # Sentence Translation
        translation_layout = QHBoxLayout()
        self.translation_input = QTextEdit()
        self.translation_input.setPlaceholderText("English translation (will be generated if empty)")
        self.translation_input.setMaximumHeight(60)
        translation_layout.addWidget(self.translation_input)
        self.generate_translation_btn = QPushButton("Generate")
        self.generate_translation_btn.clicked.connect(self._generate_translation)
        translation_layout.addWidget(self.generate_translation_btn)
        form_layout.addRow("Translation:", translation_layout)

        # Definition
        definition_layout = QHBoxLayout()
        self.definition_input = QTextEdit()
        self.definition_input.setPlaceholderText("Definition (will be looked up from JMDict)")
        self.definition_input.setMaximumHeight(80)
        definition_layout.addWidget(self.definition_input)
        self.lookup_definition_btn = QPushButton("Lookup")
        self.lookup_definition_btn.clicked.connect(self._lookup_definition)
        definition_layout.addWidget(self.lookup_definition_btn)
        form_layout.addRow("Definition:", definition_layout)

        # Audio status labels
        self.sentence_audio_label = QLabel("Not generated")
        self.word_audio_label = QLabel("Not generated")

        # Sentence Audio
        sentence_audio_layout = QHBoxLayout()
        sentence_audio_layout.addWidget(self.sentence_audio_label)
        self.generate_sentence_audio_btn = QPushButton("Generate Audio")
        self.generate_sentence_audio_btn.clicked.connect(self._generate_sentence_audio)
        sentence_audio_layout.addWidget(self.generate_sentence_audio_btn)
        form_layout.addRow("Sentence Audio:", sentence_audio_layout)

        # Word Audio
        word_audio_layout = QHBoxLayout()
        word_audio_layout.addWidget(self.word_audio_label)
        self.generate_word_audio_btn = QPushButton("Generate Audio")
        self.generate_word_audio_btn.clicked.connect(self._generate_word_audio)
        word_audio_layout.addWidget(self.generate_word_audio_btn)
        form_layout.addRow("Word Audio:", word_audio_layout)

        layout.addLayout(form_layout)

        # Store generated audio tags
        self.sentence_audio_tag = ""
        self.word_audio_tag = ""

        # Buttons
        button_layout = QHBoxLayout()

        self.generate_all_btn = QPushButton("Generate All")
        self.generate_all_btn.clicked.connect(self._generate_all)
        button_layout.addWidget(self.generate_all_btn)

        button_layout.addStretch()

        self.save_btn = QPushButton("Save Card")
        self.save_btn.clicked.connect(self._save_card)
        button_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def _on_word_changed(self, text: str):
        """Handle target word changes - auto-lookup definition."""
        if text.strip():
            self._lookup_definition()

    def _lookup_definition(self):
        """Look up the word definition in JMDict."""
        word = self.word_input.text().strip()
        if not word:
            QMessageBox.warning(self, "Warning", "Please enter a target word first.")
            return

        definition = lookup_word(word)
        if definition:
            self.definition_input.setPlainText(definition)
        else:
            self.definition_input.setPlainText("")
            # Don't show error - word might not be in dictionary

    def _generate_sentence(self):
        """Generate an example sentence using OpenAI."""
        word = self.word_input.text().strip()
        if not word:
            QMessageBox.warning(self, "Warning", "Please enter a target word first.")
            return

        progress = QProgressDialog("Generating sentence...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        try:
            definition = self.definition_input.toPlainText().strip()
            sentence = generate_sentence(word, definition if definition else None)
            self.sentence_input.setPlainText(sentence)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate sentence:\n{str(e)}")
        finally:
            progress.close()

    def _generate_translation(self):
        """Generate translation using OpenAI."""
        sentence = self.sentence_input.toPlainText().strip()
        if not sentence:
            QMessageBox.warning(self, "Warning", "Please enter or generate a sentence first.")
            return

        progress = QProgressDialog("Generating translation...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        try:
            translation = translate_sentence(sentence)
            self.translation_input.setPlainText(translation)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate translation:\n{str(e)}")
        finally:
            progress.close()

    def _generate_sentence_audio(self):
        """Generate audio for the sentence."""
        sentence = self.sentence_input.toPlainText().strip()
        if not sentence:
            QMessageBox.warning(self, "Warning", "Please enter or generate a sentence first.")
            return

        progress = QProgressDialog("Generating sentence audio...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        try:
            self.sentence_audio_tag = generate_sentence_audio(sentence)
            self.sentence_audio_label.setText("Generated ✓")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate audio:\n{str(e)}")
        finally:
            progress.close()

    def _generate_word_audio(self):
        """Generate audio for the word."""
        word = self.word_input.text().strip()
        if not word:
            QMessageBox.warning(self, "Warning", "Please enter a target word first.")
            return

        progress = QProgressDialog("Generating word audio...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        try:
            self.word_audio_tag = generate_word_audio(word)
            self.word_audio_label.setText("Generated ✓")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate audio:\n{str(e)}")
        finally:
            progress.close()

    def _generate_all(self):
        """Generate all missing fields."""
        word = self.word_input.text().strip()
        if not word:
            QMessageBox.warning(self, "Warning", "Please enter a target word first.")
            return

        progress = QProgressDialog("Generating all fields...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        try:
            # 1. Lookup definition if empty
            if not self.definition_input.toPlainText().strip():
                definition = lookup_word(word)
                if definition:
                    self.definition_input.setPlainText(definition)

            # 2. Generate sentence if empty
            if not self.sentence_input.toPlainText().strip():
                definition = self.definition_input.toPlainText().strip()
                sentence = generate_sentence(word, definition if definition else None)
                self.sentence_input.setPlainText(sentence)

            # 3. Generate translation if empty
            if not self.translation_input.toPlainText().strip():
                sentence = self.sentence_input.toPlainText().strip()
                if sentence:
                    translation = translate_sentence(sentence)
                    self.translation_input.setPlainText(translation)

            # 4. Generate word audio if not generated
            if not self.word_audio_tag:
                self.word_audio_tag = generate_word_audio(word)
                self.word_audio_label.setText("Generated ✓")

            # 5. Generate sentence audio if not generated
            sentence = self.sentence_input.toPlainText().strip()
            if sentence and not self.sentence_audio_tag:
                self.sentence_audio_tag = generate_sentence_audio(sentence)
                self.sentence_audio_label.setText("Generated ✓")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate fields:\n{str(e)}")
        finally:
            progress.close()

    def _save_card(self):
        """Save the card to Anki."""
        word = self.word_input.text().strip()
        if not word:
            QMessageBox.warning(self, "Warning", "Target word is required.")
            return

        # Get or create the note type
        try:
            model = get_or_create_note_type()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create note type:\n{str(e)}")
            return

        # Create the note
        note = Note(mw.col, model)

        # Set field values
        note["TargetWord"] = word
        note["Sentence"] = self.sentence_input.toPlainText().strip()
        note["SentenceTranslation"] = self.translation_input.toPlainText().strip()
        note["Definition"] = self.definition_input.toPlainText().strip()
        note["SentenceAudio"] = self.sentence_audio_tag
        note["WordAudio"] = self.word_audio_tag

        # Get the current deck
        deck_id = mw.col.decks.current()["id"]

        # Add the note
        try:
            mw.col.add_note(note, deck_id)
            mw.col.reset()
            QMessageBox.information(self, "Success", "Card created successfully!")
            self._clear_form()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save card:\n{str(e)}")

    def _clear_form(self):
        """Clear all form fields."""
        self.word_input.clear()
        self.sentence_input.clear()
        self.translation_input.clear()
        self.definition_input.clear()
        self.sentence_audio_tag = ""
        self.word_audio_tag = ""
        self.sentence_audio_label.setText("Not generated")
        self.word_audio_label.setText("Not generated")
