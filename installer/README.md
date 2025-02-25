# Scout Installer

This directory contains files for creating the Scout application installer.

## Requirements

To build the installer, you need:

1. **NSIS (Nullsoft Scriptable Install System)** version 3.0 or higher
   - Download from: https://nsis.sourceforge.io/Download
   - Install with all components

2. **Built Scout Application**
   - Run the build script first: `python build_executable.py`
   - Ensure the application is built in the `dist/Scout` directory

## Building the Installer

### Using the NSIS GUI

1. Right-click on `scout_installer.nsi` and select "Compile NSIS Script"
2. Wait for the compilation to complete
3. The installer will be created as `dist/Scout_Setup_1.0.0.exe`

### Using the Command Line

```
makensis installer/scout_installer.nsi
```

## Installer Features

- Multi-language support (English and German)
- Desktop and Start Menu shortcuts
- File association for .scout files
- Automatic upgrade from previous versions
- Uninstaller
- Application auto-launch option after installation

## Customization

You can customize the installer by modifying the following:

- **Graphics**:
  - `installer_header.bmp` (150x57 pixels): Header image shown on installer pages
  - `installer_welcome.bmp` (164x314 pixels): Welcome/Finish page image

- **Version Information**:
  - Edit the version constants at the top of the script

- **File Associations**:
  - Modify the `SecFileAssoc` section to change file association behavior

## Testing the Installer

It's recommended to test the installer in a virtual machine or sandbox environment before distribution.

## Troubleshooting

If you encounter issues with the installer:

1. Check the NSIS log for errors
2. Verify that all paths in the .nsi script are correct
3. Ensure all required files exist in the dist directory
4. Make sure you have administrator rights when running the installer 