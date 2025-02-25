# Scout Update System

This document provides an overview of the Scout update system, which enables the application to check for, download, and install updates automatically.

## Overview

The Scout update system provides a robust mechanism for checking for application updates, notifying users, downloading new versions, and installing them. It includes both backend logic for handling the update process and user interface components for interaction.

## Key Components

The update system consists of several components:

### 1. Update Checker (`scout/core/updater/update_checker.py`)

This component handles the core functionality of checking for, downloading, and installing updates:

- `UpdateChecker` class: Primary class for interacting with the update server
- `check_for_updates()`: Checks if a new version is available
- `download_update()`: Downloads the update installer
- `install_update()`: Launches the installer
- `get_update_checker()`: Singleton accessor function

### 2. Update Settings (`scout/core/updater/settings.py`)

This component manages user preferences for updates:

- `UpdateSettings` class: Handles loading, saving, and accessing update preferences
- Settings include:
  - Whether to check for updates on startup
  - Whether to download updates automatically
  - How often to check for updates
  - Which update channel to use (stable, beta)
- `get_update_settings()`: Singleton accessor function

### 3. Update Dialog (`scout/ui/dialogs/update_dialog.py`)

This component provides the user interface for the update system:

- `UpdateDialog` class: Main dialog for checking, downloading, and installing updates
- `DownloadThread` class: Background thread for downloading updates
- `show_update_dialog()`: Function to display the update dialog
- `check_for_updates_in_background()`: Function to check for updates in the background and notify the user

### 4. Exit Codes (`scout/core/utils/codes.py`)

This component defines exit codes for different application termination states:

- `Codes` enum: Various exit codes including `UPDATE_CODE` (10) for exiting to apply an update

## Update Process Flow

The update process follows these steps:

1. **Check for Updates**:
   - The application can check for updates on startup or when requested by the user
   - The `UpdateChecker` sends system information to the update server
   - The server responds with update information if available

2. **Notify User**:
   - If an update is available, the user is notified (if enabled in preferences)
   - The notification includes the new version number
   - The user can choose to update now or later

3. **Download Update**:
   - If the user chooses to update (or if auto-download is enabled), the update is downloaded
   - A background thread handles the download to avoid freezing the UI
   - Progress is shown to the user

4. **Install Update**:
   - After download, the user can install the update
   - The installation requires application restart
   - When the user confirms, the installer is launched
   - The application exits with `UPDATE_CODE` (10)

## Integration with Application

To integrate the update system into the main application:

1. **Startup Check**:
   ```python
   from scout.core.updater import get_update_settings, check_for_updates_in_background
   
   # In application startup
   def on_application_start():
       # ...
       
       # Check for updates if enabled in settings
       update_settings = get_update_settings()
       if update_settings.should_check_updates_on_startup():
           check_for_updates_in_background(self)
   ```

2. **Manual Check**:
   ```python
   from scout.core.updater import show_update_dialog
   
   # In "Check for Updates" menu action
   def on_check_for_updates():
       show_update_dialog(self)
   ```

3. **Handle Update Exit Code**:
   ```python
   from scout.core.utils.codes import Codes
   
   # In application launcher
   exit_code = run_application()
   
   if exit_code == Codes.UPDATE_CODE:
       print("Application exited for update")
       # Additional actions if needed
   ```

## Update Server API

The update system expects the update server to provide a REST API with the following endpoint:

- **Endpoint**: `https://api.scout-app.com/updates`
- **Method**: POST
- **Request Body**:
  ```json
  {
    "os": "Windows",
    "os_version": "10.0.19041",
    "platform": "Windows-10-10.0.19041-SP0",
    "architecture": "64bit",
    "current_version": "1.0.0"
  }
  ```
- **Response Body**:
  ```json
  {
    "latest_version": "1.0.1",
    "download_url": "https://download.scout-app.com/Scout_Setup_1.0.1.exe",
    "update_info": "This update includes bug fixes and performance improvements.",
    "changelog": "<ul><li>Fixed issue with detection</li><li>Improved performance</li></ul>"
  }
  ```

## Adding a New Update Channel

To add a new update channel (e.g., "nightly"):

1. Add the channel to the `UpdateDialog` UI:
   ```python
   self.update_channel_combo.addItem(tr("Nightly"), "nightly")
   ```

2. Update the server to handle the channel parameter:
   ```python
   # In check_for_updates
   data = {
       # ...
       "channel": self.update_settings.get_setting("update_channel", "stable")
   }
   ```

## Security Considerations

- **HTTPS**: Always use HTTPS for update server communications
- **Installer Verification**: Consider implementing signature verification for downloaded installers
- **Server Authentication**: Use proper authentication for the update server API
- **Download Path**: Store downloads in a user-specific location to avoid permission issues

## Troubleshooting

Common issues and solutions:

### Connection Issues

If the application fails to check for updates:
- Verify internet connectivity
- Check if the update server URL is correct and accessible
- Check firewall settings

### Download Issues

If updates fail to download:
- Verify download URL is correct
- Check disk space
- Check write permissions for download directory

### Installation Issues

If installation fails:
- Ensure installer was downloaded completely
- Check for administrator rights
- Try running the installer manually

## Testing

To test the update system:

1. **Mocking Update Server**:
   - Create a mock server that responds with test update data
   - Point the application to the mock server

2. **Testing With Different Versions**:
   - Create test builds with different version numbers
   - Verify the application correctly identifies newer versions

3. **End-to-End Testing**:
   - Test the complete update process from checking to installation
   - Verify the application successfully updates and maintains settings 