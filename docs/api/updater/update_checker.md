# UpdateChecker API

**Module**: `scout.core.updater.update_checker`  
**Stability**: Stable  
**Version**: 1.0  

## Overview

The `UpdateChecker` class provides functionality for checking, downloading, and installing application updates. It communicates with a remote update server to determine if new versions are available and manages the update process.

## Class Definition

### UpdateChecker

```python
class UpdateChecker:
    """
    Checks for, downloads, and installs application updates.
    
    This class handles the entire update lifecycle:
    - Checking update availability by communicating with an update server
    - Downloading update installers
    - Launching the installer to update the application
    
    It's designed as a singleton to ensure consistent update state across
    the application.
    """
```

## Properties

| Property | Type | Description |
|----------|------|-------------|
| `_current_version` | `str` | Current version of the application (private) |
| `_update_url` | `str` | URL of the update server endpoint (private) |
| `_latest_version` | `str` | Latest available version (private, set after checking) |
| `_download_url` | `str` | URL to download the update (private, set after checking) |
| `_update_info` | `str` | Description of the update (private, set after checking) |
| `_changelog` | `str` | HTML changelog of the update (private, set after checking) |

## Constructor

```python
def __init__(self, current_version: str = CURRENT_VERSION, update_url: str = UPDATE_URL)
```

Initializes the UpdateChecker with current version and update server URL.

**Parameters**:
- `current_version`: Current version of the application (default: value from module constant)
- `update_url`: URL to check for updates (default: value from module constant)

## Methods

### check_for_updates

```python
def check_for_updates(self) -> bool
```

Checks if a new version is available by querying the update server.

**Returns**:
- `True` if a newer version is available, `False` otherwise

**Raises**:
- `URLError`: If connection to the update server fails
- `HTTPError`: If the server returns an error status
- `ValueError`: If the server response is not valid JSON
- `KeyError`: If required fields are missing from the response

**Example**:
```python
checker = get_update_checker()
if checker.check_for_updates():
    print("Update available!")
else:
    print("No updates available.")
```

### download_update

```python
def download_update(self, output_dir: Optional[str] = None) -> Optional[str]
```

Downloads the update installer if an update is available.

**Parameters**:
- `output_dir`: Optional directory to save the downloaded file (default: system temp directory)

**Returns**:
- Path to the downloaded file if successful, `None` if download fails or no update is available

**Raises**:
- `URLError`: If connection to the download server fails
- `HTTPError`: If the server returns an error status
- `IOError`: If there's an error saving the file

**Example**:
```python
checker = get_update_checker()
if checker.check_for_updates():
    installer_path = checker.download_update()
    if installer_path:
        print(f"Downloaded update to: {installer_path}")
    else:
        print("Failed to download update")
```

### install_update

```python
def install_update(self, installer_path: str, silent: bool = False) -> bool
```

Launches the installer to update the application.

**Parameters**:
- `installer_path`: Path to the installer file
- `silent`: Whether to run the installer silently (default: False)

**Returns**:
- `True` if the installer was launched successfully, `False` otherwise

**Raises**:
- `FileNotFoundError`: If the installer file doesn't exist
- `OSError`: If there's an error launching the installer

**Example**:
```python
checker = get_update_checker()
if checker.check_for_updates():
    installer_path = checker.download_update()
    if installer_path:
        if checker.install_update(installer_path):
            print("Installer launched successfully")
            # Exit application with update code
            sys.exit(Codes.UPDATE_CODE)
```

### _compare_versions

```python
def _compare_versions(self, version1: str, version2: str) -> int
```

Compares two version strings using semantic versioning rules.

**Parameters**:
- `version1`: First version string
- `version2`: Second version string

**Returns**:
- `-1` if version1 < version2
- `0` if version1 == version2
- `1` if version1 > version2

**Note**: This is a private method intended for internal use only.

### get_update_info

```python
def get_update_info(self) -> Dict[str, Any]
```

Gets information about the available update.

**Returns**:
- Dictionary with update information:
  - `available`: Bool indicating if an update is available
  - `current_version`: Current version string
  - `latest_version`: Latest version string (if available)
  - `download_url`: URL to download the update (if available)
  - `update_info`: Description of the update (if available)
  - `changelog`: HTML changelog (if available)

**Example**:
```python
checker = get_update_checker()
checker.check_for_updates()
update_info = checker.get_update_info()

if update_info["available"]:
    print(f"Update available: {update_info['latest_version']}")
    print(f"Changes: {update_info['update_info']}")
```

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
checker = get_update_checker()
```

## Usage Examples

### Basic Update Check

```python
from scout.core.updater import get_update_checker

# Get the update checker
checker = get_update_checker()

# Check for updates
if checker.check_for_updates():
    # Get update information
    update_info = checker.get_update_info()
    print(f"New version available: {update_info['latest_version']}")
    print(f"Changes: {update_info['update_info']}")
    
    # Download the update
    installer_path = checker.download_update()
    if installer_path:
        # Install the update
        if checker.install_update(installer_path):
            print("Update installing, application will now exit")
            sys.exit(10)  # Update exit code
else:
    print("No updates available")
```

### Using with QApplication Exit Code

```python
from scout.core.updater import get_update_checker
from scout.core.utils.codes import Codes
from PyQt6.QtWidgets import QApplication

# In your main application code
def on_check_for_updates():
    checker = get_update_checker()
    if checker.check_for_updates():
        # Handle update process
        installer_path = checker.download_update()
        if installer_path and checker.install_update(installer_path):
            # Set application exit code and quit
            QApplication.instance().exit(Codes.UPDATE_CODE)

# In your application launcher
app = QApplication(sys.argv)
# ... app setup ...
exit_code = app.exec()

if exit_code == Codes.UPDATE_CODE:
    print("Application exited for update")
```

## Notes

- The update server expects specific JSON format for requests and responses
- Version comparison follows semantic versioning rules (MAJOR.MINOR.PATCH)
- Downloads are saved to a temporary directory by default
- The application should exit with `Codes.UPDATE_CODE` (10) when an update is being installed
- This class is designed as a singleton to ensure consistent update state across the application

## Related APIs

- [UpdateSettings](update_settings.md) - For managing update preferences
- [Codes](../utils/codes.md) - For application exit codes 