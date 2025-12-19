# Saikou - AI-Powered Japanese Vocabulary Card Creator
# Entry point for Anki add-on

from aqt import mw
from aqt.qt import QAction, QMenu

from .ui.card_dialog import CardCreatorDialog
from .ui.config_dialog import ConfigDialog
from .ui.field_mapping_dialog import FieldMappingDialog


def open_card_creator():
    """Open the Saikou card creator dialog."""
    dialog = CardCreatorDialog(mw)
    dialog.exec()


def open_config():
    """Open the configuration dialog."""
    dialog = ConfigDialog(mw)
    dialog.exec()


def open_field_mapping():
    """Open the field mapping dialog."""
    dialog = FieldMappingDialog(mw)
    dialog.exec()


# Create Saikou submenu under Tools
saikou_menu = QMenu("Saikou", mw)

create_action = QAction("Create Japanese Card", mw)
create_action.triggered.connect(open_card_creator)
saikou_menu.addAction(create_action)

field_mapping_action = QAction("Map Fields...", mw)
field_mapping_action.triggered.connect(open_field_mapping)
saikou_menu.addAction(field_mapping_action)

config_action = QAction("Configuration...", mw)
config_action.triggered.connect(open_config)
saikou_menu.addAction(config_action)

# Add Saikou submenu to Tools menu
mw.form.menuTools.addMenu(saikou_menu)
