# UpdateSettings API

**Module**: `scout.core.updater.settings`  
**Stability**: Stable  
**Version**: 1.0  

## Overview

The `UpdateSettings` class manages user preferences for the update system, including how and when to check for updates, download behavior, and notification preferences. It provides a centralized way to load, save, and access these settings throughout the application.

## Class Definition

### UpdateSettings

```python
class UpdateSettings:
    """
    Manages update settings and preferences.
    
    This class handles loading, saving, and accessing settings related to the 
    update system, such as automatic update checking and download preferences.
    """
```

## Properties

| Property | Type | Description |
|----------|------|-------------|
| `settings` | `QSettings` | The Qt settings object used for storage |
| `_settings_data` | `Dict[str, Any]` | Dictionary containing the loaded settings (private) |

## Constructor

```python
def __init__(self)
```

Initializes the UpdateSettings and loads settings from QSettings.

## Methods

### load_settings

```python
def load_settings(self) -> Dict[str, Any]
```

Loads update settings from QSettings.

**Returns**:
- Dictionary of settings with their values

**Example**:
```python
settings = get_update_settings()
settings_dict = settings.load_settings()
print(f"Check updates on startup: {settings_dict['check_updates_on_startup']}")
```

### save_settings

```python
def save_settings(self) -> None
```

Saves update settings to QSettings.

**Raises**:
- `Exception`: If there's an error saving settings

**Example**:
```python
settings = get_update_settings()
settings.set_setting("check_updates_on_startup", True)
settings.save_settings()
```

### get_setting

```python
def get_setting(self, key: str, default=None) -> Any
```

Gets a specific setting value.

**Parameters**:
- `key`: The setting key to retrieve
- `default`: Default value to return if the setting doesn't exist

**Returns**:
- The setting value, or the default if not found

**Example**:
```python
settings = get_update_settings()
check_on_startup = settings.get_setting("check_updates_on_startup", False)
```

### set_setting

```python
def set_setting(self, key: str, value: Any) -> None
```

Sets a specific setting value.

**Parameters**:
- `key`: The setting key to set
- `value`: The value to assign to the setting

**Example**:
```python
settings = get_update_settings()
settings.set_setting("check_updates_on_startup", True)
```

### should_check_updates_on_startup

```python
def should_check_updates_on_startup(self) -> bool
```

Checks if updates should be checked on application startup.

**Returns**:
- `True` if updates should be checked on startup, `False` otherwise

**Example**:
```python
settings = get_update_settings()
if settings.should_check_updates_on_startup():
    # Check for updates
```

### should_auto_download_updates

```python
def should_auto_download_updates(self) -> bool
```

Checks if updates should be downloaded automatically when available.

**Returns**:
- `True` if updates should be auto-downloaded, `False` otherwise

**Example**:
```python
settings = get_update_settings()
if settings.should_auto_download_updates():
    # Download update automatically
```

### should_notify_on_update

```python
def should_notify_on_update(self) -> bool
```

Checks if notifications should be shown when updates are available.

**Returns**:
- `True` if notifications should be shown, `False` otherwise

**Example**:
```python
settings = get_update_settings()
if settings.should_notify_on_update():
    # Show notification
```

### update_last_check_time

```python
def update_last_check_time(self, time_str: str) -> None
```

Updates the timestamp of the last update check.

**Parameters**:
- `time_str`: ISO formatted time string

**Example**:
```python
from datetime import datetime
import iso8601

settings = get_update_settings()
now = datetime.now().isoformat()
settings.update_last_check_time(now)
```

## Module Constants

### DEFAULT_SETTINGS

```python
DEFAULT_SETTINGS = {
    "check_updates_on_startup": True,  # Check for updates when application starts
    "auto_download_updates": False,    # Automatically download available updates
    "notify_on_update": True,          # Show notification when update is available
    "last_check_time": None,           # Last time updates were checked (ISO format)
    "check_frequency_days": 1,         # How often to check for updates (in days)
    "update_channel": "stable",        # Update channel (stable, beta, etc.)
}
```

Default settings used when no stored settings are found.

## Module Functions

### get_update_settings

```python
def get_update_settings() -> UpdateSettings
```

Gets the singleton instance of the UpdateSettings.

**Returns**:
- The UpdateSettings singleton instance

**Example**:
```python
settings = get_update_settings()
```

## Usage Examples

### Changing Update Preferences

```python
from scout.core.updater import get_update_settings

# Get the update settings
settings = get_update_settings()

# Change multiple settings
settings.set_setting("check_updates_on_startup", True)
settings.set_setting("auto_download_updates", False)
settings.set_setting("notify_on_update", True)
settings.set_setting("check_frequency_days", 7)
settings.set_setting("update_channel", "beta")

# Save the changes
settings.save_settings()
```

### Checking Update Conditions

```python
from scout.core.updater import get_update_settings
from datetime import datetime, timedelta
import iso8601

settings = get_update_settings()

# Check if we should perform an update check
should_check = settings.should_check_updates_on_startup()

# Check how long since last check
last_check = settings.get_setting("last_check_time")
check_frequency = settings.get_setting("check_frequency_days", 1)

if last_check:
    last_check_datetime = iso8601.parse_date(last_check)
    time_since_check = datetime.now() - last_check_datetime
    if time_since_check > timedelta(days=check_frequency):
        # Time to check again
        should_check = True

if should_check:
    # Perform update check
    pass
```

### Implementation in Settings UI

```python
from PyQt6.QtWidgets import QCheckBox, QComboBox
from scout.core.updater import get_update_settings
from scout.ui.utils.language_manager import tr

# In a settings UI class
def _load_update_settings(self):
    settings = get_update_settings()
    
    # Load settings to UI components
    self.check_on_startup.setChecked(
        settings.get_setting("check_updates_on_startup", True)
    )
    self.auto_download.setChecked(
        settings.get_setting("auto_download_updates", False)
    )
    self.notify_on_update.setChecked(
        settings.get_setting("notify_on_update", True)
    )
    
    # Set update channel
    channel = settings.get_setting("update_channel", "stable")
    index = self.channel_combo.findData(channel)
    if index >= 0:
        self.channel_combo.setCurrentIndex(index)

def _save_update_settings(self):
    settings = get_update_settings()
    
    # Save settings from UI components
    settings.set_setting(
        "check_updates_on_startup", 
        self.check_on_startup.isChecked()
    )
    settings.set_setting(
        "auto_download_updates", 
        self.auto_download.isChecked()
    )
    settings.set_setting(
        "notify_on_update", 
        self.notify_on_update.isChecked()
    )
    
    # Save update channel
    channel = self.channel_combo.currentData()
    settings.set_setting("update_channel", channel)
    
    # Save all settings
    settings.save_settings()
```

## Notes

- Settings are loaded automatically when the UpdateSettings instance is created
- Changes to settings are not persisted until `save_settings()` is called
- Boolean settings loaded from QSettings may need conversion (handled internally)
- The UpdateSettings class follows the singleton pattern for consistent access across the application

## Related APIs

- [UpdateChecker](update_checker.md) - For checking and installing updates 