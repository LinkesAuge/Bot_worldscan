# Updates and Version Management

This guide explains how the Scout application handles updates and version management.

## Automatic Updates

Scout includes an automatic update system that can check for, download, and install updates. This helps you stay up to date with the latest features and improvements without having to manually check and download updates.

### Update Settings

You can customize how the application handles updates through the Settings tab. The following options are available:

- **Check for updates on startup**: When enabled, the application will automatically check for updates when it starts.
- **Automatically download updates**: When enabled, updates will be downloaded automatically when available.
- **Show notification when updates are available**: When enabled, you'll be notified when updates are available.
- **Check frequency**: Controls how often the application checks for updates (daily, weekly, or monthly).
- **Update channel**: Controls which update channel to use:
  - **Stable**: Recommended for most users. Only receives stable, tested updates.
  - **Beta**: For users who want to test new features early. May contain bugs.

To access these settings:
1. Open the Settings tab
2. Navigate to the "Updates" section
3. Adjust the settings as desired
4. Click "Save" to apply the changes

![Update Settings](../images/update_settings.png)

### Manual Update Check

You can manually check for updates at any time:

1. From the File menu, select **Check for Updates**
2. The application will check for available updates
3. If an update is available, you'll see details about the new version
4. You can choose to download and install the update immediately, or defer until later

![Update Dialog](../images/update_dialog.png)

### Update Process

When an update is available, the following process is used:

1. **Notification**: If enabled, you'll see a notification that an update is available.
2. **Details**: The update dialog shows information about the new version, including version number and changes.
3. **Download**: Click the "Download" button to download the update installer.
4. **Install**: After downloading, click "Install Now" to install the update.
5. **Restart**: The application will close and the installer will run to update Scout.

### Command Line Options

Scout provides command line options for controlling update behavior:

- `--check-updates`: Forces checking for updates on startup, even if disabled in settings.
- `--no-check-updates`: Disables checking for updates on startup, even if enabled in settings.

Example:
```bash
# Force update check
scout --check-updates

# Disable update check
scout --no-check-updates
```

## Version Information

### Checking Current Version

To check the current version of Scout:

1. From the Help menu, select **About Scout**
2. The version number is displayed in the about dialog

### Version History

Scout uses semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Increments for incompatible changes
- **MINOR**: Increments for new features
- **PATCH**: Increments for bug fixes

### Changelogs

The update dialog displays a changelog showing what's new in each update. This helps you understand what changes have been made and which bugs have been fixed.

## Troubleshooting Updates

### Update Fails to Download

If an update fails to download:

1. Check your internet connection
2. Verify that any firewalls or security software isn't blocking the download
3. Try the update again by selecting **Check for Updates** from the File menu
4. If the problem persists, you can download the update manually from the official website

### Update Fails to Install

If an update fails to install:

1. Make sure you have administrator privileges
2. Close any other instances of Scout that might be running
3. Verify that antivirus software isn't blocking the installer
4. Try restarting your computer and attempting the update again

### Reverting to a Previous Version

If you encounter issues with a new version and need to revert to a previous version:

1. Visit the official Scout website
2. Navigate to the "Downloads" section
3. Locate and download the previous version
4. Uninstall the current version
5. Install the previous version 