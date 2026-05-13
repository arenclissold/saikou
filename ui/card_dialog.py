# Card creator dialog for Saikou

import os
import re
from typing import Callable

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
from ..services.gemini_client import generate_sentence, translate_sentence, get_sentence_with_fallback, generate_and_translate
from ..services.google_tts import generate_word_audio, generate_sentence_audio, get_media_folder
from ..utils import get_config


def get_field_mapping() -> dict:
    """Get the field mapping configuration."""
    config = get_config()
    return config.get("field_mapping", {})


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


class GenerationWorker(QThread):
    """Worker thread for long-running generation tasks."""

    succeeded = pyqtSignal(str, object)  # task name, result
    failed = pyqtSignal(str, str)  # task name, error message

    def __init__(self, task_name: str, task_func: Callable[[], object]):
        super().__init__()
        self.task_name = task_name
        self.task_func = task_func

    def run(self):
        """Run the generation task in a background thread."""
        try:
            self.succeeded.emit(self.task_name, self.task_func())
        except Exception as e:
            self.failed.emit(self.task_name, str(e))


class CardCreatorDialog(QDialog):
    """Dialog for creating Japanese vocabulary cards with AI assistance."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Saikou - Create Card")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(700)

        # Debounce timer for dictionary search
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(500)  # 500ms debounce
        self._search_timer.timeout.connect(self._do_search)

        # Current workers
        self._search_worker = None
        self._details_worker = None
        self._generation_workers = {}
        self._generation_callbacks = {}
        self._generate_all_tasks = set()
        self._generate_all_active = False

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
        api_key = config.get("google_api_key", "").strip()

        if not api_key:
            warning_text = (
                '⚠️ Google API key not configured. '
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
        # Extract filename from [sound:filename]
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

    def _is_generation_task_running(self, task_name: str) -> bool:
        """Check whether a generation task is already running."""
        worker = self._generation_workers.get(task_name)
        return bool(worker and worker.isRunning())

    def _set_buttons_busy(self, buttons, busy_text: str):
        """Disable buttons and return their original labels."""
        original_texts = []
        for button in buttons:
            original_texts.append(button.text())
            button.setEnabled(False)
            button.setText(busy_text)
        return original_texts

    def _restore_buttons(self, buttons, original_texts):
        """Restore buttons after a background task finishes."""
        for button, text in zip(buttons, original_texts):
            button.setText(text)
            button.setEnabled(True)

    def _start_generation_task(
        self,
        task_name: str,
        buttons,
        busy_text: str,
        task_func: Callable[[], object],
        on_success: Callable[[object], None],
        error_prefix: str,
        on_finished: Callable[[], None] = None,
    ) -> bool:
        """Start a long-running task without blocking the UI."""
        if self._is_generation_task_running(task_name):
            return False

        if not isinstance(buttons, (list, tuple)):
            buttons = [buttons]

        original_texts = self._set_buttons_busy(buttons, busy_text)
        worker = GenerationWorker(task_name, task_func)
        self._generation_workers[task_name] = worker
        self._generation_callbacks[task_name] = {
            "buttons": buttons,
            "original_texts": original_texts,
            "on_success": on_success,
            "error_prefix": error_prefix,
            "on_finished": on_finished,
        }

        worker.succeeded.connect(self._on_generation_task_succeeded)
        worker.failed.connect(self._on_generation_task_failed)
        worker.finished.connect(lambda name=task_name: self._cleanup_generation_worker(name))
        worker.start()
        return True

    def _cleanup_generation_worker(self, task_name: str):
        """Release a finished generation worker."""
        worker = self._generation_workers.pop(task_name, None)
        if worker:
            worker.deleteLater()

    def _finish_generation_task(self, task_name: str):
        """Restore UI state for a finished generation task."""
        callback = self._generation_callbacks.pop(task_name, None)
        if not callback:
            return

        self._restore_buttons(callback["buttons"], callback["original_texts"])
        on_finished = callback.get("on_finished")
        if on_finished:
            on_finished()

    def _on_generation_task_succeeded(self, task_name: str, result: object):
        """Apply a completed generation task result."""
        callback = self._generation_callbacks.get(task_name)
        if not callback:
            return

        try:
            callback["on_success"](result)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"{callback['error_prefix']}:\n{str(e)}")
        finally:
            self._finish_generation_task(task_name)

    def _on_generation_task_failed(self, task_name: str, error_message: str):
        """Show a generation task error and restore its button."""
        callback = self._generation_callbacks.get(task_name)
        if callback:
            QMessageBox.critical(self, "Error", f"{callback['error_prefix']}:\n{error_message}")
        self._finish_generation_task(task_name)

    def _set_generate_all_active(self, active: bool):
        """Update Generate All button state without blocking the dialog."""
        self._generate_all_active = active
        self.generate_all_btn.setEnabled(not active)
        self.generate_all_btn.setText("Generating..." if active else "Generate All")

    def _track_generate_all_task(self, task_name: str):
        """Track a task started by Generate All."""
        self._generate_all_tasks.add(task_name)

    def _finish_generate_all_task(self, task_name: str):
        """Mark one Generate All task as finished."""
        self._generate_all_tasks.discard(task_name)
        if self._generate_all_active and not self._generate_all_tasks:
            self._set_generate_all_active(False)

    def _start_generate_all_task(
        self,
        task_name: str,
        buttons,
        busy_text: str,
        task_func: Callable[[], object],
        on_success: Callable[[object], None],
        error_prefix: str,
    ) -> bool:
        """Start and track a task as part of Generate All."""
        started = self._start_generation_task(
            task_name,
            buttons,
            busy_text,
            task_func,
            on_success,
            error_prefix,
            on_finished=lambda name=task_name: self._finish_generate_all_task(name),
        )
        if started:
            self._track_generate_all_task(task_name)
        return started

    def _lookup_definition(self):
        """Manual lookup button - also async."""
        word = self.word_input.text().strip()
        if not word:
            QMessageBox.warning(self, "Warning", "Please enter a target word first.")
            return

        self._start_generation_task(
            "definition",
            self.lookup_definition_btn,
            "Looking...",
            lambda: lookup_word(word),
            self._apply_definition_result,
            "Failed to look up definition",
        )

    def _apply_definition_result(self, definition: object):
        """Apply a definition lookup result."""
        if definition:
            self.definition_input.setPlainText(str(definition))

    def _generate_sentence(self):
        """Generate an example sentence using Tatoeba first, then falling back to AI."""
        word = self.word_input.text().strip()
        if not word:
            QMessageBox.warning(self, "Warning", "Please enter a target word first.")
            return

        definition = self.definition_input.toPlainText().strip()
        self._start_generation_task(
            "sentence",
            self.generate_sentence_btn,
            "Generating...",
            lambda: get_sentence_with_fallback(word, definition if definition else None),
            self._apply_sentence_result,
            "Failed to generate sentence",
        )

    def _apply_sentence_result(self, sentence: object):
        """Apply a generated sentence."""
        self.sentence_input.setPlainText(str(sentence))

    def _generate_translation(self):
        """Generate translation using Google Gemini."""
        sentence = self.sentence_input.toPlainText().strip()
        if not sentence:
            QMessageBox.warning(self, "Warning", "Please enter or generate a sentence first.")
            return

        self._start_generation_task(
            "translation",
            self.generate_translation_btn,
            "Generating...",
            lambda: translate_sentence(sentence),
            self._apply_translation_result,
            "Failed to generate translation",
        )

    def _apply_translation_result(self, translation: object):
        """Apply a generated translation."""
        self.translation_input.setPlainText(str(translation))

    def _generate_sentence_audio(self):
        """Generate audio for the sentence."""
        sentence = self.sentence_input.toPlainText().strip()
        if not sentence:
            QMessageBox.warning(self, "Warning", "Please enter or generate a sentence first.")
            return

        self._start_generation_task(
            "sentence_audio",
            self.generate_sentence_audio_btn,
            "Generating...",
            lambda: generate_sentence_audio(sentence),
            self._apply_sentence_audio_result,
            "Failed to generate audio",
        )

    def _apply_sentence_audio_result(self, sound_tag: object):
        """Apply generated sentence audio."""
        self.sentence_audio_tag = str(sound_tag)
        self.play_sentence_audio_btn.setEnabled(True)

    def _generate_word_audio(self):
        """Generate audio for the word."""
        word = self.word_input.text().strip()
        if not word:
            QMessageBox.warning(self, "Warning", "Please enter a target word first.")
            return

        self._start_generation_task(
            "word_audio",
            self.generate_word_audio_btn,
            "Generating...",
            lambda: generate_word_audio(word),
            self._apply_word_audio_result,
            "Failed to generate audio",
        )

    def _apply_word_audio_result(self, sound_tag: object):
        """Apply generated word audio."""
        self.word_audio_tag = str(sound_tag)
        self.play_word_audio_btn.setEnabled(True)

    def _generate_all(self):
        """Generate all missing fields."""
        word = self.word_input.text().strip()
        if not word:
            QMessageBox.warning(self, "Warning", "Please enter a target word first.")
            return

        self._set_generate_all_active(True)
        started_any = False

        # Word audio is independent, so it can run immediately.
        if not self.word_audio_tag:
            started_any = self._start_generate_all_task(
                "word_audio",
                self.generate_word_audio_btn,
                "Generating...",
                lambda word=word: generate_word_audio(word),
                self._apply_word_audio_result,
                "Failed to generate word audio",
            ) or started_any

        if not self.definition_input.toPlainText().strip():
            started_any = self._start_generate_all_task(
                "definition",
                self.lookup_definition_btn,
                "Looking...",
                lambda word=word: lookup_word(word),
                lambda definition, word=word: self._apply_generate_all_definition(definition, word),
                "Failed to look up definition",
            ) or started_any
        else:
            started_any = self._continue_generate_all_after_definition(word) or started_any

        if not started_any:
            self._set_generate_all_active(False)

    def _apply_generate_all_definition(self, definition: object, word: str):
        """Apply definition result and continue Generate All dependencies."""
        self._apply_definition_result(definition)
        self._continue_generate_all_after_definition(word)

    def _continue_generate_all_after_definition(self, word: str) -> bool:
        """Continue Generate All after definition is available."""
        sentence = self.sentence_input.toPlainText().strip()
        translation = self.translation_input.toPlainText().strip()
        definition = self.definition_input.toPlainText().strip()

        if not sentence:
            return self._start_generate_all_task(
                "sentence_translation",
                [self.generate_sentence_btn, self.generate_translation_btn],
                "Generating...",
                lambda word=word, definition=definition: generate_and_translate(word, definition if definition else None),
                self._apply_generate_all_sentence_translation,
                "Failed to generate sentence and translation",
            )

        if not translation:
            return self._start_generate_all_task(
                "translation",
                self.generate_translation_btn,
                "Generating...",
                lambda sentence=sentence: translate_sentence(sentence),
                lambda translation: self._apply_generate_all_translation(translation),
                "Failed to generate translation",
            )

        return self._start_generate_all_sentence_audio()

    def _apply_generate_all_sentence_translation(self, result: object):
        """Apply combined sentence/translation result and continue audio generation."""
        sentence, translation = result
        self.sentence_input.setPlainText(sentence)
        if translation and not self.translation_input.toPlainText().strip():
            self.translation_input.setPlainText(translation)
        self._start_generate_all_sentence_audio()

    def _apply_generate_all_translation(self, translation: object):
        """Apply translation result and continue audio generation."""
        self._apply_translation_result(translation)
        self._start_generate_all_sentence_audio()

    def _start_generate_all_sentence_audio(self) -> bool:
        """Start sentence audio generation if Generate All still needs it."""
        sentence = self.sentence_input.toPlainText().strip()
        if not sentence or self.sentence_audio_tag:
            return False

        return self._start_generate_all_task(
            "sentence_audio",
            self.generate_sentence_audio_btn,
            "Generating...",
            lambda sentence=sentence: generate_sentence_audio(sentence),
            self._apply_sentence_audio_result,
            "Failed to generate sentence audio",
        )

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
        self._search_timer.stop()
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.terminate()
            self._search_worker.wait()
        if self._details_worker and self._details_worker.isRunning():
            self._details_worker.terminate()
            self._details_worker.wait()
        for worker in list(self._generation_workers.values()):
            if worker.isRunning():
                worker.terminate()
                worker.wait()
        super().closeEvent(event)
