# GitHub Release Template

This document provides a template and guidelines for creating GitHub releases for the Scout application.

## Release Title Format

Use the following format for release titles:

```
Scout v{MAJOR}.{MINOR}.{PATCH} - {RELEASE_NAME}
```

Examples:
- `Scout v1.0.0 - Final Release`
- `Scout v1.1.0 - Summer Update`
- `Scout v1.0.1 - Maintenance Update`

For pre-releases, add the appropriate suffix:
- `Scout v1.1.0-beta.1 - New Features Preview`
- `Scout v1.0.0-rc.2 - Release Candidate 2`

## Release Description Template

```markdown
# Scout v{VERSION} - {RELEASE_NAME}

**Release Date:** {YYYY-MM-DD}

## Overview

Brief description of this release (2-3 sentences). Highlight the most significant changes or features.

## New Features

* **Feature Name** - Detailed description of the feature
* **Another Feature** - Description of another significant feature
* ...

## Improvements

* **Area of Improvement** - Description of the improvement
* **Another Improvement** - Description of another improvement
* ...

## Bug Fixes

* **Bug Description** - What was fixed and how it affects users
* **Another Bug** - Description of another bug fix
* ...

## Known Issues

* Issue description and possible workarounds
* Another known issue
* ...

## Breaking Changes

* Description of any breaking changes and migration steps
* Another breaking change
* ...

## Installation Instructions

### Windows
Download and run the installer. Follow the on-screen instructions to complete the installation.

### macOS
Download the DMG file, open it, and drag Scout to your Applications folder.

### Linux
Different methods available:
* **AppImage**: Download, make executable (`chmod +x Scout-{VERSION}-x86_64.AppImage`), and run.
* **Debian Package**: Download and install with `sudo dpkg -i scout_{VERSION}_amd64.deb`

## System Requirements

* **Operating System**: Windows 10/11, macOS 11+, or Ubuntu 20.04+
* **Processor**: Dual-core CPU @ 2.0 GHz or better
* **Memory**: 4 GB RAM minimum, 8 GB recommended
* **Display**: 1366x768 resolution minimum
* **Storage**: 500 MB available space

## Documentation

The full documentation for this release is available at:
* [User Guide](https://github.com/yourusername/scout/blob/v{VERSION}/docs/user_guide/)
* [Release Notes](https://github.com/yourusername/scout/blob/v{VERSION}/docs/RELEASE_NOTES.md)

## Checksums

SHA-256 checksums for verification:

```
{SHA256_HASH} Scout_Setup_{VERSION}.exe
{SHA256_HASH} Scout_{VERSION}.dmg
{SHA256_HASH} Scout-{VERSION}-x86_64.AppImage
{SHA256_HASH} scout_{VERSION}_amd64.deb
```

## Acknowledgments

Thanks to all contributors who helped make this release possible!
{LIST_OF_CONTRIBUTORS}
```

## Attachment Guidelines

Each release should include the following attachments:

### Windows Assets
- `Scout_Setup_1.0.0.exe` - Windows installer
- `Scout_1.0.0_Windows_Portable.zip` - Portable version (optional)

### macOS Assets
- `Scout_1.0.0.dmg` - macOS disk image
- `Scout_1.0.0_macOS.zip` - Direct application bundle (optional)

### Linux Assets
- `Scout-1.0.0-x86_64.AppImage` - Linux AppImage
- `scout_1.0.0_amd64.deb` - Debian package
- `scout-1.0.0.tar.gz` - Generic Linux tarball (optional)

### Documentation
- `Scout_1.0.0_ReleaseNotes.pdf` - PDF version of release notes (optional)

### Checksums
- `Scout_1.0.0_SHA256SUMS.txt` - Text file with SHA-256 checksums for all assets

## Release Process Checklist

Before publishing a release, ensure the following tasks are completed:

1. **Pre-Release Preparation**
   - [ ] Version numbers updated in all relevant files
   - [ ] Release notes completed and reviewed
   - [ ] CHANGELOG.md updated
   - [ ] Git tag created (`git tag -a v1.0.0 -m "Scout v1.0.0"`)

2. **Build Process**
   - [ ] Windows installer built and tested
   - [ ] macOS package built and tested
   - [ ] Linux packages built and tested
   - [ ] SHA-256 checksums generated for all assets

3. **Documentation**
   - [ ] User guide updated for the new version
   - [ ] API documentation updated (if applicable)
   - [ ] Screenshots updated to reflect the current version

4. **Quality Assurance**
   - [ ] Installation tested on all platforms
   - [ ] Upgrade from previous version tested
   - [ ] Basic functionality verified on all platforms
   - [ ] All listed bug fixes verified

5. **Release Publishing**
   - [ ] Create new GitHub release using this template
   - [ ] Upload all build assets
   - [ ] Verify download links work correctly
   - [ ] Publish release (or publish as pre-release if applicable)

6. **Post-Release Actions**
   - [ ] Update website with new version information
   - [ ] Send announcement to appropriate channels
   - [ ] Update the in-app update system to recognize the new version
   - [ ] Monitor initial user feedback and issues

## Generating Checksums

```bash
# Windows (PowerShell)
Get-FileHash Scout_Setup_1.0.0.exe -Algorithm SHA256 | Format-List

# macOS/Linux
shasum -a 256 Scout_1.0.0.dmg
shasum -a 256 Scout-1.0.0-x86_64.AppImage
shasum -a 256 scout_1.0.0_amd64.deb
``` 