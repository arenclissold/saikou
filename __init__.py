# Saikou - AI-Powered Japanese Vocabulary Card Creator
# Entry point for Anki add-on

from aqt import mw, gui_hooks
from aqt.qt import QAction, QMenu

from .ui.card_dialog import CardCreatorDialog
from .ui.config_dialog import ConfigDialog


def open_card_creator():
    """Open the Saikou card creator dialog."""
    dialog = CardCreatorDialog(mw)
    dialog.exec()


def open_config():
    """Open the configuration dialog."""
    dialog = ConfigDialog(mw)
    dialog.exec()


def setup_menu():
    """Create the Saikou menu in the menu bar."""
    # Create the Saikou menu
    saikou_menu = QMenu("Saikou", mw)

    # Add "Create Japanese Card" action
    create_action = QAction("Create Japanese Card", mw)
    create_action.triggered.connect(open_card_creator)
    saikou_menu.addAction(create_action)

    # Add separator
    saikou_menu.addSeparator()

    # Add "Configuration..." action
    config_action = QAction("Configuration...", mw)
    config_action.triggered.connect(open_config)
    saikou_menu.addAction(config_action)

    # Add the menu to the menu bar (before Help menu)
    mw.form.menubar.insertMenu(mw.form.menuHelp.menuAction(), saikou_menu)


# Use Anki's hook system to initialize after profile is loaded
gui_hooks.profile_did_open.append(setup_menu)
