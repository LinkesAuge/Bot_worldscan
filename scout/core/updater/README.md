# Scout Update System

This package provides the update system for the Scout application, allowing for automatic update checking, downloading, and installation.

## Package Structure

- `__init__.py` - Package initialization and convenient access functions
- `update_checker.py` - Core class for checking, downloading, and installing updates
- `settings.py` - Settings management for update preferences
- `utils.py` - Utility functions for the update system

## Key Components

### UpdateChecker

The main class responsible for interacting with the update server, checking for updates, downloading update files, and launching the installer.

```python
from scout.core.updater import get_update_checker

# Get the singleton instance
checker = get_update_checker()

# Check for updates
update_available = checker.check_for_updates()

# Get update info
update_info = checker.get_update_info()

# Download the update
installer_path = checker.download_update()

# Install the update
checker.install_update(installer_path)
```

### UpdateSettings

Manages user preferences for updates, including automatic checking, download behavior, and notification settings.

```python
from scout.core.updater import get_update_settings

# Get the singleton instance
settings = get_update_settings()

# Check current settings
should_check = settings.should_check_updates_on_startup()
should_download = settings.should_auto_download_updates()
should_notify = settings.should_notify_on_update()

# Update settings
settings.set_setting("check_updates_on_startup", True)
settings.set_setting("auto_download_updates", False)
settings.save_settings()
```

### UpdateDialog

A dialog for displaying update information to the user and handling the download and installation process.

```python
from scout.core.updater import show_update_dialog

# Show the update dialog
show_update_dialog(parent_widget)

# Show the dialog and check for updates automatically
show_update_dialog(parent_widget, check_automatically=True)
```

### Background Update Checking

```python
from scout.core.updater import check_for_updates_in_background

# Check for updates in the background and notify the user if available
check_for_updates_in_background(parent_widget)
```

## Update Process

1. **Check**: The application checks for updates either on startup (if enabled in settings) or when the user manually checks.
2. **Notification**: If an update is available, the user is notified based on their notification preferences.
3. **Download**: The user can download the update, or it may be downloaded automatically based on settings.
4. **Install**: The user chooses to install the update, which launches the installer and exits the application.
5. **Restart**: After installation, the user starts the updated application.

## Update Server API

The update system communicates with the update server via HTTPS:

### Request Format

```json
{
  "os": "Windows",
  "os_version": "10.0.19041",
  "platform": "Windows-10-10.0.19041-SP0",
  "architecture": "64bit",
  "current_version": "1.0.0",
  "channel": "stable"
}
```

### Response Format

```json
{
  "latest_version": "1.0.1",
  "download_url": "https://download.example.com/Scout_Setup_1.0.1.exe",
  "update_info": "This update includes bug fixes and performance improvements.",
  "changelog": "<ul><li>Fixed issue with detection</li><li>Improved performance</li></ul>"
}
```

## Testing the Update System

A mock update server is provided in `tools/mock_update_server.py` for testing the update system without requiring a public server.

```bash
# Start mock server
python tools/mock_update_server.py --latest-version 1.0.1

# Run application with mock server
python main.py --check-updates
```

## Integration

The update system is integrated with the main application in:

1. `main.py` - Handles update command-line arguments and exit codes
2. `scout/ui/main_window.py` - Adds menu items and startup check functionality

## Extending the Update System

The update system is designed to be extensible. Common extensions include:

- Adding new update channels (e.g., beta, nightly)
- Implementing update verification for security
- Adding automatic installation options
- Creating a delta update mechanism for smaller downloads

See the developer documentation for more details on extending the update system. 