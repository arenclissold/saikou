# Saikou - AI-Powered Japanese Vocabulary Card Creator
# Entry point for Anki add-on

from aqt import mw
from aqt import gui_hooks
from aqt.qt import QAction, QMenu, QTimer

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


def setup_menu():
    """Set up the Saikou menu in the menu bar."""
    if not mw or not mw.form or not mw.form.menubar:
        return

    # Check if menu already exists and get it
    saikou_menu = None
    saikou_action = None
    for action in mw.form.menubar.actions():
        if action.text() == "Saikou":
            saikou_menu = action.menu()
            saikou_action = action
            break

    # If menu doesn't exist, create it
    if not saikou_menu:
        saikou_menu = QMenu("Saikou", mw)

        # Insert Saikou menu before Help menu
        help_menu = mw.form.menuHelp
        if help_menu:
            saikou_action = mw.form.menubar.insertMenu(help_menu.menuAction(), saikou_menu)
        else:
            # Fallback: add to end if Help menu not found
            saikou_action = mw.form.menubar.addMenu(saikou_menu)

    # Clear existing actions to avoid duplicates
    saikou_menu.clear()

    # Add all menu items
    create_action = QAction("Create Card", mw)
    create_action.triggered.connect(open_card_creator)
    saikou_menu.addAction(create_action)

    field_mapping_action = QAction("Map Fields...", mw)
    field_mapping_action.triggered.connect(open_field_mapping)
    saikou_menu.addAction(field_mapping_action)

    # Add separator
    saikou_menu.addSeparator()

    # Add Settings action
    settings_action = QAction("Settings", mw)
    settings_action.triggered.connect(open_config)
    saikou_menu.addAction(settings_action)

    # Force macOS menu refresh by removing and re-adding the menu
    if saikou_action:
        # Temporarily hide and show to force refresh
        saikou_action.setVisible(False)
        saikou_action.setVisible(True)

    # Force menu update
    saikou_menu.update()
    saikou_menu.repaint()

    # Also update the menu bar
    if mw.form.menubar:
        mw.form.menubar.update()
        mw.form.menubar.repaint()

    action_texts = [
        action.text() if action.text() else "(separator)"
        for action in saikou_menu.actions()
    ]
    if "Settings" not in action_texts:
        print(f"ERROR: Settings not found in menu! Actions: {action_texts}")

# Set up menu when main window is ready
# Use a hook to ensure menu is created after window is fully initialized


def on_profile_loaded():
    """Set up menu after profile is loaded."""
    setup_menu()

gui_hooks.profile_did_open.append(on_profile_loaded)

# Also try to set up immediately if window is already ready
# Use a timer to delay slightly and avoid macOS menu caching issues


def delayed_setup():
    """Set up menu with a slight delay to avoid macOS caching."""
    if mw and mw.form and mw.form.menubar:
        try:
            setup_menu()
        except Exception as e:
            print(f"Error setting up menu: {e}")

if mw and mw.form and mw.form.menubar:
    # Delay by 100ms to let macOS finish menu initialization
    QTimer.singleShot(100, delayed_setup)

# Set custom config action to use our dialog instead of default JSON editor


def addon_config_action():
    """Custom config action called from add-on manager."""
    dialog = ConfigDialog(mw)
    dialog.exec()

# Get add-on name (package name from __name__)
addon_name = __name__.split(".")[0]
mw.addonManager.setConfigAction(addon_name, addon_config_action)
