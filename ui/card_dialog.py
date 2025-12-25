# Card creator dialog for Saikou

import os
import re

from aqt.qt import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QMessageBox,
    QProgressDialog,
    QTimer,
    QThread,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    pyqtSignal,
    Qt,
)
from aqt import mw
from aqt.sound import av_player
from anki.notes import Note

from ..services.jmdict import lookup_word, search_words, get_word_details
from ..services.openai_client import generate_sentence, translate_sentence, get_sentence_with_fallback, generate_and_translate
from ..services.audio import generate_word_audio, generate_sentence_audio, get_media_folder


def get_addon_name() -> str:
    """Get the add-on folder name."""
    return __name__.split(".")[0]


def get_config() -> dict:
    """Get the current configuration."""
    return mw.addonManager.getConfig(get_addon_name()) or {}


def get_field_mapping() -> dict:
    """Get the field mapping configuration."""
    config = get_config()
    return config.get("field_mapping", {})


class LookupWorker(QThread):
    """Worker thread for async dictionary lookup."""

    finished = pyqtSignal(str)  # definition or empty string

    def __init__(self, word: str):
        super().__init__()
        self.word = word

    def run(self):
        """Perform the lookup in background thread."""
        try:
            definition = lookup_word(self.word)
            self.finished.emit(definition or "")
        except Exception:
            self.finished.emit("")


class SearchWorker(QThread):
    """Worker thread for async dictionary search."""

    finished = pyqtSignal(list)  # list of search results

    def __init__(self, query: str):
        super().__init__()
        self.query = query

    def run(self):
        """Perform the search in background thread."""
        try:
            results = search_words(self.query, limit=20)
            self.finished.emit(results)
        except Exception:
            self.finished.emit([])


class WordDetailsWorker(QThread):
    """Worker thread for async word details lookup."""

    finished = pyqtSignal(dict)  # word details dict

    def __init__(self, word: str):
        super().__init__()
        self.word = word

    def run(self):
        """Get word details in background thread."""
        try:
            details = get_word_details(self.word)
            self.finished.emit(details or {})
        except Exception:
            self.finished.emit({})


class CardCreatorDialog(QDialog):
    """Dialog for creating Japanese vocabulary cards with AI assistance."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Saikou - Create Card")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(700)

        # Debounce timer for word lookup
        self._lookup_timer = QTimer()
        self._lookup_timer.setSingleShot(True)
        self._lookup_timer.setInterval(300)  # 300ms debounce
        self._lookup_timer.timeout.connect(self._do_lookup)

        # Debounce timer for dictionary search
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(500)  # 500ms debounce
        self._search_timer.timeout.connect(self._do_search)

        # Current workers
        self._lookup_worker = None
        self._search_worker = None
        self._details_worker = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI using standard widgets."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Create splitter for left/right panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left panel - Dictionary search
        left_panel = self._create_dictionary_panel()
        splitter.addWidget(left_panel)

        # Right panel - Card creator
        right_panel = self._create_card_creator_panel()
        splitter.addWidget(right_panel)

        # Set splitter proportions (40% left, 60% right)
        splitter.setSizes([400, 600])

        main_layout.addWidget(splitter)

    def _create_dictionary_panel(self):
        """Create the left dictionary search panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title_label = QLabel("Dictionary Search")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # Search input
        search_layout = QHBoxLayout()
        search_layout.setSpacing(5)
        self.dict_search_input = QLineEdit()
        self.dict_search_input.setPlaceholderText("Search dictionary...")
        self.dict_search_input.textChanged.connect(self._on_search_changed)
        self.dict_search_input.returnPressed.connect(self._trigger_search)
        self.dict_search_input.setMinimumHeight(32)
        search_layout.addWidget(self.dict_search_input)

        clear_btn = QPushButton("✕")
        clear_btn.setFixedWidth(32)
        clear_btn.setFixedHeight(32)
        clear_btn.setToolTip("Clear search")
        clear_btn.clicked.connect(self.dict_search_input.clear)
        search_layout.addWidget(clear_btn)

        layout.addLayout(search_layout)

        # Search results list
        results_label = QLabel("Results")
        results_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(results_label)

        self.search_results_list = QListWidget()
        self.search_results_list.itemClicked.connect(self._on_result_selected)
        layout.addWidget(self.search_results_list)

        # Word details display
        details_label = QLabel("Word Details")
        details_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(details_label)

        self.word_details_display = QTextEdit()
        self.word_details_display.setReadOnly(True)
        self.word_details_display.setMaximumHeight(200)
        layout.addWidget(self.word_details_display)

        # Use word button
        use_word_btn = QPushButton("Use This Word")
        use_word_btn.clicked.connect(self._use_selected_word)
        layout.addWidget(use_word_btn)

        return panel

    def _create_card_creator_panel(self):
        """Create the right card creator panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title_label = QLabel("Card Creator")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # Deck display
        deck_info_layout = QHBoxLayout()
        deck_info_layout.setSpacing(5)
        deck_label = QLabel("Deck:")
        deck_label.setStyleSheet("font-weight: bold;")
        deck_info_layout.addWidget(deck_label)
        self.deck_display_label = QLabel("(Not configured)")
        self.deck_display_label.setStyleSheet("color: #888;")
        deck_info_layout.addWidget(self.deck_display_label)
        deck_info_layout.addStretch()
        layout.addLayout(deck_info_layout)

        # Update deck display
        self._update_deck_display()

        # API key warning
        self.api_key_warning_label = QLabel()
        self.api_key_warning_label.setWordWrap(True)
        self.api_key_warning_label.setStyleSheet("color: #d32f2f; padding: 8px; background-color: #ffebee; border-radius: 4px;")
        self.api_key_warning_label.setVisible(False)
        layout.addWidget(self.api_key_warning_label)
        self._check_api_key()

        # Form layout for fields
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        # Target Word (required)
        word_layout = QHBoxLayout()
        word_layout.setSpacing(5)
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("The word you want to learn")
        self.word_input.textChanged.connect(self._on_word_changed)
        self.word_input.setMinimumHeight(32)
        word_layout.addWidget(self.word_input)
        self.generate_all_btn = QPushButton("Generate All")
        self.generate_all_btn.setFixedWidth(100)
        self.generate_all_btn.clicked.connect(self._generate_all)
        word_layout.addWidget(self.generate_all_btn)
        form_layout.addRow("Target Word", word_layout)

        # Sentence
        sentence_layout = QHBoxLayout()
        sentence_layout.setSpacing(5)
        self.sentence_input = QTextEdit()
        self.sentence_input.setPlaceholderText("Example sentence (will be generated if empty)")
        self.sentence_input.setMaximumHeight(60)
        sentence_layout.addWidget(self.sentence_input)
        self.generate_sentence_btn = QPushButton("Generate")
        self.generate_sentence_btn.setFixedWidth(80)
        self.generate_sentence_btn.clicked.connect(self._generate_sentence)
        sentence_layout.addWidget(self.generate_sentence_btn)
        form_layout.addRow("Sentence", sentence_layout)

        # Sentence Translation
        translation_layout = QHBoxLayout()
        translation_layout.setSpacing(5)
        self.translation_input = QTextEdit()
        self.translation_input.setPlaceholderText("English translation (will be generated if empty)")
        self.translation_input.setMaximumHeight(60)
        translation_layout.addWidget(self.translation_input)
        self.generate_translation_btn = QPushButton("Generate")
        self.generate_translation_btn.setFixedWidth(80)
        self.generate_translation_btn.clicked.connect(self._generate_translation)
        translation_layout.addWidget(self.generate_translation_btn)
        form_layout.addRow("Translation", translation_layout)

        # Definition
        definition_layout = QHBoxLayout()
        definition_layout.setSpacing(5)
        self.definition_input = QTextEdit()
        self.definition_input.setPlaceholderText("Definition (auto-looked up from Jisho)")
        self.definition_input.setMaximumHeight(100)
        definition_layout.addWidget(self.definition_input)
        self.lookup_definition_btn = QPushButton("Lookup")
        self.lookup_definition_btn.setFixedWidth(80)
        self.lookup_definition_btn.clicked.connect(self._lookup_definition)
        definition_layout.addWidget(self.lookup_definition_btn)
        form_layout.addRow("Definition", definition_layout)

        # Sentence Audio
        sentence_audio_layout = QHBoxLayout()
        sentence_audio_layout.setSpacing(5)
        self.play_sentence_audio_btn = QPushButton("▶")
        self.play_sentence_audio_btn.setFixedWidth(32)
        self.play_sentence_audio_btn.setFixedHeight(32)
        self.play_sentence_audio_btn.setToolTip("Play audio")
        self.play_sentence_audio_btn.clicked.connect(self._play_sentence_audio)
        self.play_sentence_audio_btn.setEnabled(False)
        sentence_audio_layout.addWidget(self.play_sentence_audio_btn)
        self.generate_sentence_audio_btn = QPushButton("Generate")
        self.generate_sentence_audio_btn.setFixedWidth(80)
        self.generate_sentence_audio_btn.clicked.connect(self._generate_sentence_audio)
        sentence_audio_layout.addWidget(self.generate_sentence_audio_btn)
        form_layout.addRow("Sentence Audio", sentence_audio_layout)

        # Word Audio
        word_audio_layout = QHBoxLayout()
        word_audio_layout.setSpacing(5)
        self.play_word_audio_btn = QPushButton("▶")
        self.play_word_audio_btn.setFixedWidth(32)
        self.play_word_audio_btn.setFixedHeight(32)
        self.play_word_audio_btn.setToolTip("Play audio")
        self.play_word_audio_btn.clicked.connect(self._play_word_audio)
        self.play_word_audio_btn.setEnabled(False)
        word_audio_layout.addWidget(self.play_word_audio_btn)
        self.generate_word_audio_btn = QPushButton("Generate")
        self.generate_word_audio_btn.setFixedWidth(80)
        self.generate_word_audio_btn.clicked.connect(self._generate_word_audio)
        word_audio_layout.addWidget(self.generate_word_audio_btn)
        form_layout.addRow("Word Audio", word_audio_layout)

        layout.addLayout(form_layout)
        layout.addStretch()

        # Store generated audio tags
        self.sentence_audio_tag = ""
        self.word_audio_tag = ""
        self._selected_word = None

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        button_layout.addStretch()

        self.save_btn = QPushButton("Save Card")
        self.save_btn.clicked.connect(self._save_card)
        self._update_save_button_state()
        button_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        return panel

    def _update_deck_display(self):
        """Update the deck display label based on field mapping configuration."""
        field_mapping = get_field_mapping()
        deck_name = field_mapping.get("deck_name", "")

        if deck_name:
            self.deck_display_label.setText(deck_name)
            self.deck_display_label.setStyleSheet("")
        else:
            self.deck_display_label.setText("(Not configured)")
            self.deck_display_label.setStyleSheet("color: #888;")

        # Also update save button state when deck display updates
        self._update_save_button_state()

    def _check_api_key(self):
        """Check if API key is configured and show warning if not."""
        config = get_config()
        api_key = config.get("openai_api_key", "").strip()

        if not api_key:
            warning_text = (
                '⚠️ OpenAI API key not configured. '
                '<a href="config">Configure API key</a> to generate sentences, translations, and audio.'
            )
            self.api_key_warning_label.setText(warning_text)
            self.api_key_warning_label.setOpenExternalLinks(False)
            # Disconnect first to avoid multiple connections
            try:
                self.api_key_warning_label.linkActivated.disconnect()
            except TypeError:
                pass  # No existing connection
            self.api_key_warning_label.linkActivated.connect(self._open_config)
            self.api_key_warning_label.setVisible(True)
        else:
            self.api_key_warning_label.setVisible(False)

    def _open_config(self, link: str):
        """Open the configuration dialog."""
        from .config_dialog import ConfigDialog
        config_dialog = ConfigDialog(self)
        result = config_dialog.exec()
        # Recheck API key after config dialog closes
        if result == QDialog.DialogCode.Accepted:
            self._check_api_key()
        # Ensure focus returns to the card dialog
        self.activateWindow()
        self.raise_()

    def _update_save_button_state(self):
        """Enable/disable save button based on field mapping configuration."""
        # Check if save_btn exists (might not be created yet during initialization)
        if not hasattr(self, 'save_btn') or self.save_btn is None:
            return

        field_mapping = get_field_mapping()
        mappings = field_mapping.get("mappings", {})

        # Check if at least target_word is mapped
        has_target_word = bool(mappings.get("target_word"))

        self.save_btn.setEnabled(has_target_word)
        if not has_target_word:
            self.save_btn.setToolTip("Please configure field mappings first (Tools → Saikou → Map Fields...)")
        else:
            self.save_btn.setToolTip("")

    def _on_search_changed(self, text: str):
        """Handle dictionary search input changes - debounced."""
        self._search_timer.stop()

        if text.strip():
            self._search_timer.start()
        else:
            self.search_results_list.clear()
            self.word_details_display.clear()

    def _trigger_search(self):
        """Trigger search immediately when Enter is pressed."""
        self._search_timer.stop()
        self._do_search()

    def _do_search(self):
        """Perform the dictionary search (called after debounce)."""
        query = self.dict_search_input.text().strip()
        if not query:
            return

        # Cancel any running search worker
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.terminate()
            self._search_worker.wait()

        # Clear previous results
        self.search_results_list.clear()
        self.search_results_list.addItem("Searching...")

        # Start new search worker
        self._search_worker = SearchWorker(query)
        self._search_worker.finished.connect(self._on_search_finished)
        self._search_worker.start()

    def _on_search_finished(self, results: list):
        """Handle search results from worker thread."""
        self.search_results_list.clear()

        if not results:
            self.search_results_list.addItem("No results found")
            return

        for result in results:
            word_text = result.get("word", "")
            reading = result.get("reading", "")
            definition = result.get("definition", "")

            # Create display text
            if reading and reading != word_text:
                display_text = f"{word_text} ({reading})"
            else:
                display_text = word_text

            # Show first line of definition
            if definition:
                first_line = definition.split("\n")[0]
                if len(first_line) > 50:
                    first_line = first_line[:50] + "..."
                display_text += f" - {first_line}"

            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, result)
            self.search_results_list.addItem(item)

    def _on_result_selected(self, item: QListWidgetItem):
        """Handle selection of a search result."""
        result = item.data(Qt.ItemDataRole.UserRole)
        if not result:
            return

        word_text = result.get("word", "")
        self._selected_word = word_text

        # Cancel any running details worker
        if self._details_worker and self._details_worker.isRunning():
            self._details_worker.terminate()
            self._details_worker.wait()

        # Show loading
        self.word_details_display.setPlainText("Loading details...")

        # Get full word details
        self._details_worker = WordDetailsWorker(word_text)
        self._details_worker.finished.connect(self._on_details_finished)
        self._details_worker.start()

    def _on_details_finished(self, details: dict):
        """Handle word details from worker thread."""
        if not details:
            self.word_details_display.setPlainText("No details available")
            return

        word_text = details.get("word", "")
        reading = details.get("reading", "")
        definition = details.get("definition", "")

        # Format display
        display_text = f"Word: {word_text}\n"
        if reading and reading != word_text:
            display_text += f"Reading: {reading}\n"
        display_text += f"\nDefinition:\n{definition}"

        self.word_details_display.setPlainText(display_text)

    def _use_selected_word(self):
        """Use the selected word to populate card creator fields."""
        if not self._selected_word:
            QMessageBox.warning(self, "Warning", "Please select a word from the search results first.")
            return

        # Get word details
        details = get_word_details(self._selected_word)
        if not details:
            QMessageBox.warning(self, "Warning", "Could not load word details.")
            return

        # Populate fields
        self.word_input.setText(details.get("word", ""))
        self.definition_input.setPlainText(details.get("definition", ""))

    def _get_audio_path(self, sound_tag: str) -> str:
        """Extract the full file path from a sound tag."""
        # Extract filename from [sound:filename.mp3]
        match = re.search(r'\[sound:(.+?)\]', sound_tag)
        if match:
            filename = match.group(1)
            return os.path.join(get_media_folder(), filename)
        return ""

    def _play_sentence_audio(self):
        """Play the generated sentence audio."""
        if self.sentence_audio_tag:
            audio_path = self._get_audio_path(self.sentence_audio_tag)
            if audio_path and os.path.exists(audio_path):
                av_player.play_file(audio_path)

    def _play_word_audio(self):
        """Play the generated word audio."""
        if self.word_audio_tag:
            audio_path = self._get_audio_path(self.word_audio_tag)
            if audio_path and os.path.exists(audio_path):
                av_player.play_file(audio_path)

    def _on_word_changed(self, text: str):
        """Handle target word changes - debounced auto-lookup."""
        # Cancel any pending lookup
        self._lookup_timer.stop()

        if text.strip():
            # Start debounce timer
            self._lookup_timer.start()

    def _do_lookup(self):
        """Perform the actual lookup (called after debounce)."""
        word = self.word_input.text().strip()
        if not word:
            return

        # Cancel any running worker
        if self._lookup_worker and self._lookup_worker.isRunning():
            self._lookup_worker.terminate()
            self._lookup_worker.wait()

        # Start new worker
        self._lookup_worker = LookupWorker(word)
        self._lookup_worker.finished.connect(self._on_lookup_finished)
        self._lookup_worker.start()

    def _on_lookup_finished(self, definition: str):
        """Handle lookup result from worker thread."""
        if definition:
            self.definition_input.setPlainText(definition)
        # Don't clear if no definition - user might have typed something

    def _lookup_definition(self):
        """Manual lookup button - also async."""
        word = self.word_input.text().strip()
        if not word:
            QMessageBox.warning(self, "Warning", "Please enter a target word first.")
            return

        # Cancel any pending debounced lookup
        self._lookup_timer.stop()

        # Do immediate lookup
        self._do_lookup()

    def _generate_sentence(self):
        """Generate an example sentence using Tatoeba first, then falling back to AI."""
        word = self.word_input.text().strip()
        if not word:
            QMessageBox.warning(self, "Warning", "Please enter a target word first.")
            return

        progress = QProgressDialog("Searching for example sentence...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        try:
            definition = self.definition_input.toPlainText().strip()
            # Try Tatoeba first, fall back to AI if not found
            sentence = get_sentence_with_fallback(word, definition if definition else None)
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
            self.play_sentence_audio_btn.setEnabled(True)
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
            self.play_word_audio_btn.setEnabled(True)
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

            # 2. Generate sentence and translation if empty
            if not self.sentence_input.toPlainText().strip():
                definition = self.definition_input.toPlainText().strip()
                # Try Tatoeba first (which includes translation), fall back to AI
                sentence, translation = generate_and_translate(word, definition if definition else None)
                self.sentence_input.setPlainText(sentence)
                # If translation wasn't already filled, set it
                if not self.translation_input.toPlainText().strip() and translation:
                    self.translation_input.setPlainText(translation)
            elif not self.translation_input.toPlainText().strip():
                # Sentence exists but translation doesn't - generate translation
                sentence = self.sentence_input.toPlainText().strip()
                if sentence:
                    translation = translate_sentence(sentence)
                    self.translation_input.setPlainText(translation)

            # 4. Generate word audio if not generated
            if not self.word_audio_tag:
                self.word_audio_tag = generate_word_audio(word)
                self.play_word_audio_btn.setEnabled(True)

            # 5. Generate sentence audio if not generated
            sentence = self.sentence_input.toPlainText().strip()
            if sentence and not self.sentence_audio_tag:
                self.sentence_audio_tag = generate_sentence_audio(sentence)
                self.play_sentence_audio_btn.setEnabled(True)

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

        # Get field mapping configuration
        field_mapping = get_field_mapping()
        if not field_mapping.get("notetype_id"):
            QMessageBox.warning(
                self,
                "Warning",
                "Please configure field mappings first.\n"
                "Go to Tools → Saikou → Map Fields..."
            )
            return

        # Get the note type
        notetype_id = field_mapping.get("notetype_id")
        model = mw.col.models.get(notetype_id)
        if not model:
            QMessageBox.critical(
                self,
                "Error",
                f"Note type not found. Please reconfigure field mappings."
            )
            return

        # Create the note
        note = Note(mw.col, model)

        # Get field mappings
        mappings = field_mapping.get("mappings", {})

        # Map Saikou fields to note fields
        field_values = {
            "target_word": word,
            "sentence": self.sentence_input.toPlainText().strip(),
            "sentence_translation": self.translation_input.toPlainText().strip(),
            "definition": self.definition_input.toPlainText().strip(),
            "sentence_audio": self.sentence_audio_tag,
            "word_audio": self.word_audio_tag,
        }

        # Set field values based on mappings
        for saikou_field, note_field in mappings.items():
            if note_field and saikou_field in field_values:
                try:
                    note[note_field] = field_values[saikou_field]
                except KeyError:
                    pass  # Field doesn't exist in note type

        # Get the deck
        deck_id = field_mapping.get("deck_id")
        if not deck_id:
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
        self.play_sentence_audio_btn.setEnabled(False)
        self.play_word_audio_btn.setEnabled(False)
        self._selected_word = None

    def closeEvent(self, event):
        """Clean up on close."""
        self._lookup_timer.stop()
        self._search_timer.stop()
        if self._lookup_worker and self._lookup_worker.isRunning():
            self._lookup_worker.terminate()
            self._lookup_worker.wait()
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.terminate()
            self._search_worker.wait()
        if self._details_worker and self._details_worker.isRunning():
            self._details_worker.terminate()
            self._details_worker.wait()
        super().closeEvent(event)
