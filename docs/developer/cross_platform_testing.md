# Cross-Platform Testing Plan

## Overview

This document outlines the testing strategy for ensuring that the Scout application works correctly across different operating systems (Windows, macOS, and Linux). It covers test infrastructure, test cases, and procedures for validating platform-specific behaviors.

## Supported Platforms

Scout is designed to work on the following platforms:

1. **Windows**: Primary development platform
   - Windows 10 (64-bit)
   - Windows 11 (64-bit)

2. **macOS**: Secondary platform
   - macOS 10.15 (Catalina) and newer
   - Both Intel and Apple Silicon support

3. **Linux**: Secondary platform
   - Ubuntu 20.04 LTS and newer
   - Debian 11 and newer
   - Other distributions with appropriate dependencies

## Platform-Specific Functionality

The following areas require platform-specific testing:

### 1. File System Operations

- File paths (separators, absolute vs. relative)
- Default directories (Documents, AppData, etc.)
- File permissions and attributes
- File dialogs

### 2. Window Management

- Window capture methods
- Window positioning and sizing
- Multi-monitor support
- DPI scaling

### 3. User Interface

- Styling and themes
- Keyboard shortcuts
- Menu structures
- Dialog behavior

### 4. Update and Installation

- Installer behavior
- Update installation process
- Default installation locations
- Service integration

### 5. System Integration

- File associations
- Startup behavior
- Notification system integration
- Operating system permissions

## Test Infrastructure

### Platform Utility Module

The `scout/tests/cross_platform/platform_utils.py` module provides utilities for:

- Detecting the current platform
- Simulating different platforms for testing
- Getting platform-specific information
- Conditionally running or skipping tests based on platform

### Test Runner

The `scout/tests/cross_platform/run_platform_tests.py` script runs platform-specific tests and generates reports:

```bash
# Run all platform tests
python -m scout.tests.cross_platform.run_platform_tests

# Run specific tests
python -m scout.tests.cross_platform.run_platform_tests --pattern test_ui_platform.py

# Generate a report
python -m scout.tests.cross_platform.run_platform_tests --report reports/platform_report.json
```

### Test Mocking

For simulating different platforms:

```python
from scout.tests.cross_platform.platform_utils import PlatformContext, PlatformType

# Simulate Windows environment
with PlatformContext(PlatformType.WINDOWS):
    # Test code here - sys.platform will report as 'win32'
    ...
```

## Test Cases

### 1. Update System Tests

- Test update checking across platforms
- Verify installer launch behavior
- Test platform-specific update process

### 2. UI Tests

- Test platform-appropriate styling
- Verify file dialogs use correct default locations
- Test keyboard shortcuts for platform conventions
- Verify platform-specific icons and visuals

### 3. File Path Tests

- Test path normalization
- Verify path joining works correctly
- Test handling of absolute and relative paths
- Verify platform-specific path separators

## Continuous Integration

Platform tests should be run regularly as part of the CI/CD pipeline:

1. **Windows CI**: Run on Windows runners as part of every PR
2. **macOS CI**: Run on macOS runners for tagged releases and nightly builds
3. **Linux CI**: Run on Ubuntu runners for tagged releases and nightly builds

## Manual Testing Procedure

In addition to automated tests, manual testing should be performed before each release:

1. Build the application on each supported platform
2. Verify installation process
3. Run through platform-specific test checklist
4. Verify update functionality
5. Test system integration features

## Platform-Specific Test Checklists

### Windows Testing Checklist

- [ ] Installation works correctly via NSIS installer
- [ ] Application starts from Start Menu shortcut
- [ ] File associations work correctly
- [ ] Update process works with Windows permissions
- [ ] Standard application folders are correct
- [ ] Window capture works on various Windows versions
- [ ] Shortcuts follow Windows conventions (Ctrl+C, Ctrl+V, etc.)

### macOS Testing Checklist

- [ ] Application bundle structure is correct
- [ ] Application launches properly from Applications folder
- [ ] Shortcuts follow macOS conventions (Cmd+C, Cmd+V, etc.)
- [ ] File dialogs show correct default locations
- [ ] Update process respects macOS security features
- [ ] Window capture works with macOS permissions
- [ ] Proper behavior with Apple Silicon vs Intel hardware

### Linux Testing Checklist

- [ ] Installation via package works correctly
- [ ] Dependencies are properly specified and installed
- [ ] X11 window capture works correctly
- [ ] File system permissions are respected
- [ ] Standard Linux directory structure is followed
- [ ] Update process handles package manager interactions
- [ ] Keyboard shortcuts follow Linux conventions

## Reporting Issues

Platform-specific issues should be reported with:

1. Platform details (OS version, architecture, etc.)
2. Steps to reproduce
3. Expected vs actual behavior
4. Screenshots or videos where applicable
5. Logs from the platform test runner

## Adding New Platform Tests

When adding new platform-specific functionality:

1. Identify platform differences that need testing
2. Create test cases in the `scout/tests/cross_platform` directory
3. Use `PlatformContext` for simulating different platforms
4. Add conditional logic for platform-specific expectations
5. Update the relevant platform test checklist

## Interpreting Test Results

The platform test runner generates reports that include:

- Platform information (OS, version, architecture)
- Test results summary (passed, failed, skipped)
- Detailed failure information
- Overall success rate

Success criteria:
- All critical functionality tests should pass on all supported platforms
- Minor UI differences may be acceptable if documented
- Platform-specific features should work correctly on their target platform 