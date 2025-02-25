# Update Mechanism

This document provides a technical overview of the Scout application's update mechanism for developers who want to understand, test, or extend this functionality.

## Overview

The update system is designed to provide a seamless update experience for users while maintaining flexibility and security. It consists of multiple components that work together to check for, download, and install updates.

## Architecture

The update system is implemented with the following components:

### Core Components

1. **UpdateChecker** (`scout/core/updater/update_checker.py`)
   - Handles checking for updates via the update server API
   - Downloads update installer files
   - Launches the installer process
   - Maintains singleton pattern for central access

2. **UpdateSettings** (`scout/core/updater/settings.py`)
   - Manages user preferences related to updates
   - Saves/loads settings using QSettings
   - Provides accessor methods for update preferences
   - Maintains singleton pattern for consistent access

3. **UpdateDialog** (`scout/ui/dialogs/update_dialog.py`)
   - UI for displaying update information
   - Handles the download process with progress reporting
   - Provides controls for installing updates
   - Includes settings controls for update preferences

4. **Background Workers** (`scout/ui/dialogs/update_dialog.py`)
   - `DownloadThread` for non-blocking download operations
   - Reports progress and completion signals

### System Integration

1. **Application Integration** (`scout/ui/main_window.py`)
   - Integration with main window menu
   - Startup update checks based on settings
   - Auto-update checks with configurable frequency

2. **Exit Handling** (`main.py`)
   - Special exit code (10) for update-related application termination
   - Clean shutdown for update installation

## Update Process Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Application    │────▶│  UpdateChecker  │────▶│  Update Server  │
│                 │     │                 │     │                 │
└────────┬────────┘     └─────────────────┘     └────────┬────────┘
         │                                               │
         │                                               │
         │            ┌─────────────────┐                │
         │            │                 │                │
         └───────────▶│  UpdateDialog   │◀───────────────┘
                      │                 │
                      └────────┬────────┘
                               │
                               │
                      ┌────────┴────────┐
                      │                 │
                      │  Installer      │
                      │                 │
                      └─────────────────┘
```

### Checking for Updates

The update check process follows these steps:

1. The application requests an update check via `get_update_checker().check_for_updates()`
2. The `UpdateChecker` collects system information and current version
3. This data is sent to the update server via HTTPS POST
4. The server determines if an update is available
5. The server returns update information (version, URL, changes)
6. `UpdateChecker` compares versions to determine if update is newer
7. Result is returned to the application

### Downloading Updates

The download process follows these steps:

1. The application requests download via `get_update_checker().download_update()`
2. A temporary directory is created for the download
3. The installer is downloaded using `urllib`
4. Progress is monitored and reported (if using `DownloadThread`)
5. The downloaded file path is returned on success

### Installing Updates

The installation process follows these steps:

1. The application requests installation via `get_update_checker().install_update()`
2. The application prepares for shutdown
3. The installer is launched using `subprocess.Popen`
4. The application exits with code `Codes.UPDATE_CODE` (10)
5. The installer updates the application

## API Reference

### UpdateChecker API

```python
class UpdateChecker:
    def check_for_updates() -> bool:
        """
        Check if a new version is available.
        
        Returns:
            True if update is available, False otherwise
        """

    def download_update(output_dir: Optional[str] = None) -> Optional[str]:
        """
        Download the update installer.
        
        Args:
            output_dir: Optional directory for download
            
        Returns:
            Path to downloaded file, or None if download failed
        """

    def install_update(installer_path: str, silent: bool = False) -> bool:
        """
        Launch the installer to update the application.
        
        Args:
            installer_path: Path to installer file
            silent: Whether to run installer silently
            
        Returns:
            True if installer was launched successfully
        """

    def get_update_info() -> Dict[str, Any]:
        """
        Get information about available update.
        
        Returns:
            Dictionary with update information:
            - available: True if update is available
            - current_version: Current version string
            - latest_version: Latest version string
            - download_url: URL to download installer
            - update_info: Description of update
            - changelog: HTML changelog
        """
```

### UpdateSettings API

```python
class UpdateSettings:
    def load_settings() -> Dict[str, Any]:
        """
        Load update settings from QSettings.
        
        Returns:
            Dictionary of settings
        """

    def save_settings() -> None:
        """
        Save update settings to QSettings.
        """

    def get_setting(key: str, default=None) -> Any:
        """
        Get a specific setting value.
        """

    def set_setting(key: str, value: Any) -> None:
        """
        Set a specific setting value.
        """

    def should_check_updates_on_startup() -> bool:
        """
        Check if updates should be checked on startup.
        """

    def should_auto_download_updates() -> bool:
        """
        Check if updates should be downloaded automatically.
        """

    def should_notify_on_update() -> bool:
        """
        Check if notifications should be shown for available updates.
        """
```

### Module Functions

```python
def get_update_checker() -> UpdateChecker:
    """
    Get the singleton update checker instance.
    """

def get_update_settings() -> UpdateSettings:
    """
    Get the singleton update settings instance.
    """

def show_update_dialog(parent=None, check_automatically: bool = True) -> int:
    """
    Show the update dialog.
    
    Args:
        parent: Parent widget
        check_automatically: Whether to check for updates automatically
        
    Returns:
        Dialog result code
    """

def check_for_updates_in_background(parent=None) -> bool:
    """
    Check for updates in the background and notify if available.
    
    Args:
        parent: Parent widget
        
    Returns:
        True if update check was initiated
    """
```

## Update Server API

The update system communicates with the update server via HTTP(S):

### Request

- **Endpoint**: `UPDATE_URL` (configured in `update_checker.py`)
- **Method**: POST
- **Content-Type**: application/json
- **Body**:
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

### Response

- **Status Code**: 200 OK
- **Content-Type**: application/json
- **Body**:
  ```json
  {
    "latest_version": "1.0.1",
    "download_url": "https://download.scout-app.com/Scout_Setup_1.0.1.exe",
    "update_info": "This update includes bug fixes and performance improvements.",
    "changelog": "<ul><li>Fixed issue with detection</li><li>Improved performance</li></ul>"
  }
  ```

## Testing the Update System

### Using the Mock Update Server

A mock update server is provided for testing the update system without requiring an actual server:

1. Run the mock server:
   ```bash
   python tools/mock_update_server.py --latest-version 1.0.1
   ```

2. Configure the update checker to use the mock server:
   ```python
   from scout.core.updater.update_checker import get_update_checker
   
   checker = get_update_checker()
   checker._update_url = "http://localhost:8000/updates"
   ```

3. Test the update check:
   ```python
   has_update = checker.check_for_updates()
   print(f"Update available: {has_update}")
   print(f"Update info: {checker.get_update_info()}")
   ```

### Unit Testing

Unit tests for the update system are located in:
- `scout/tests/core/updater/test_update_checker.py`
- `scout/tests/core/updater/test_update_settings.py`

Run these tests with:
```bash
pytest scout/tests/core/updater/
```

## Common Extension Scenarios

### Adding a New Update Channel

To add a new update channel (e.g., "nightly"):

1. Update the channel dropdown in `UpdateDialog._create_ui()`:
   ```python
   self.update_channel_combo.addItem(tr("Nightly"), "nightly")
   ```

2. Ensure the server handles the new channel value

### Implementing Update Verification

To implement update verification for security:

1. Add signature verification to `download_update()`:
   ```python
   def download_update(self, output_dir: Optional[str] = None) -> Optional[str]:
       # ... existing code ...
       
       # Verify download signature
       if not self._verify_signature(downloaded_file):
           logger.error("Invalid update signature")
           return None
       
       return downloaded_file
   ```

2. Implement the verification method:
   ```python
   def _verify_signature(self, file_path: str) -> bool:
       # Implement signature verification logic
       # ...
       return True
   ```

### Adding Auto-Update Support

To implement fully automatic updates:

1. Update `UpdateSettings` with a new preference:
   ```python
   DEFAULT_SETTINGS["auto_install_updates"] = False
   ```

2. Add UI control in `UpdateDialog._create_ui()`:
   ```python
   self.auto_install_check = QCheckBox(tr("Automatically install updates"))
   self.settings_layout.addWidget(self.auto_install_check)
   ```

3. Implement automatic installation logic in background check:
   ```python
   def check_for_updates_in_background(parent=None) -> bool:
       # ... existing code ...
       
       if update_available:
           if get_update_settings().get_setting("auto_install_updates", False):
               # Auto download and install
               # ...
   ```

## Security Considerations

When working with the update system, consider the following security aspects:

1. **HTTPS Communication**: Always use HTTPS for update server communication
2. **Installer Verification**: Consider implementing hash or signature verification
3. **Secure Download Location**: Use a secure hosting provider for installer files
4. **User Consent**: Always get user consent before installing updates
5. **Fallback Mechanism**: Provide means to recover from failed updates

## Troubleshooting Development Issues

### Update Check Issues

If update checks are failing during development:
- Check if the update URL is correct and accessible
- Verify network connectivity
- Check if JSON request/response format is correct
- Use the mock server for isolated testing

### Download Issues

If update downloads are failing:
- Check if the download URL is correct and accessible
- Verify file permissions for the download directory
- Check for disk space issues

### Installation Issues

If updates are not installing correctly:
- Verify the installer is executable
- Check if the application is properly closing before installation
- Verify installer command-line parameters 