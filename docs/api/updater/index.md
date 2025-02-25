# Updater API

**Module**: `scout.core.updater`  
**Stability**: Stable  
**Version**: 1.0  

## Overview

The Scout Update System provides functionality for checking, downloading, and installing application updates. This module contains components for managing the update lifecycle and user preferences related to updates.

## Components

### Core Classes

| Class | Description |
|-------|-------------|
| [UpdateChecker](update_checker.md) | Checks for, downloads, and installs application updates |
| [UpdateSettings](update_settings.md) | Manages user preferences for update behavior |

### Imported UI Components

| Component | Description |
|-----------|-------------|
| UpdateDialog | Dialog for displaying update information and handling user interaction |
| DownloadThread | Background thread for downloading updates |

## Module Functions

### get_update_checker

```python
def get_update_checker() -> UpdateChecker
```

Gets the singleton instance of the UpdateChecker.

**Returns**:
- The UpdateChecker singleton instance

**Example**:
```python
from scout.core.updater import get_update_checker

checker = get_update_checker()
if checker.check_for_updates():
    print("Update available!")
```

### get_update_settings

```python
def get_update_settings() -> UpdateSettings
```

Gets the singleton instance of the UpdateSettings.

**Returns**:
- The UpdateSettings singleton instance

**Example**:
```python
from scout.core.updater import get_update_settings

settings = get_update_settings()
if settings.should_check_updates_on_startup():
    # Check for updates
```

### show_update_dialog

```python
def show_update_dialog(parent=None, check_automatically: bool = True) -> int
```

Shows the update dialog and optionally checks for updates.

**Parameters**:
- `parent`: Parent widget (optional)
- `check_automatically`: Whether to check for updates automatically when the dialog opens (default: True)

**Returns**:
- Dialog result code

**Example**:
```python
from scout.core.updater import show_update_dialog

# Show update dialog and check for updates automatically
result = show_update_dialog(self)
```

### check_for_updates_in_background

```python
def check_for_updates_in_background(parent=None) -> bool
```

Checks for updates in the background and shows a notification if an update is available.

**Parameters**:
- `parent`: Parent widget (optional)

**Returns**:
- `True` if the update check was initiated, `False` otherwise

**Example**:
```python
from scout.core.updater import check_for_updates_in_background

# Check for updates in the background on application startup
def on_startup():
    # ... other initialization ...
    check_for_updates_in_background(main_window)
```

## Usage Patterns

### Basic Update Check Workflow

```python
from scout.core.updater import get_update_checker, show_update_dialog

# Option 1: Just show the dialog (it will check for updates automatically)
show_update_dialog(parent_window)

# Option 2: Check programmatically first
checker = get_update_checker()
if checker.check_for_updates():
    # Show dialog only if update is available
    show_update_dialog(parent_window, check_automatically=False)
    print("Update is available")
else:
    print("No updates available")
```

### Background Update Check

```python
from scout.core.updater import check_for_updates_in_background, get_update_settings

# Check settings first
settings = get_update_settings()
if settings.should_check_updates_on_startup():
    # Only check if enabled in settings
    check_for_updates_in_background(main_window)
```

### Update Menu Integration

```python
from PyQt6.QtWidgets import QMenu, QAction
from scout.core.updater import show_update_dialog

# In a menu setup method
def setup_menu(self):
    # Create Help menu
    help_menu = self.menuBar().addMenu(tr("Help"))
    
    # Add Check for Updates action
    check_updates_action = QAction(tr("Check for Updates"), self)
    check_updates_action.triggered.connect(self._on_check_for_updates)
    help_menu.addAction(check_updates_action)

# Handler method
def _on_check_for_updates(self):
    show_update_dialog(self)
```

## Notes

- The update system is designed for Windows applications using NSIS installers
- Update checks require internet connectivity and can be configured by users
- The system uses semantic versioning (MAJOR.MINOR.PATCH) for version comparison
- A mock update server is provided for testing (`tools/mock_update_server.py`)

## Related Resources

- [Update System User Guide](../../user_guide/updates.md) - User documentation
- [Update System Technical Documentation](../../developer/update_mechanism.md) - Developer guide 