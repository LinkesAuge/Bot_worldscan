# Scout - Game Automation and Detection Tool

[![Release Version](https://img.shields.io/badge/release-v1.0.0-blue.svg)](https://github.com/yourusername/scout/releases/tag/v1.0.0)
[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Scout is a powerful automation and computer vision tool designed for the Total Battle game. It detects and interacts with game elements, automates repetitive tasks, and analyzes game state. Version 1.0.0 is now available with full multilingual support, error recovery, and cross-platform compatibility.

<p align="center">
  <img src="resources/icons/scout.ico" alt="Scout Logo" width="128">
</p>

## Features

### 🔍 Game Detection
- **Window Detection**: Automatically finds and tracks the game window in both standalone and browser versions
- **Computer Vision**: Multiple detection strategies for identifying game elements:
  - Template Matching for visual pattern recognition
  - OCR (Optical Character Recognition) for text extraction
  - YOLO object detection for complex elements (optional)
- **Real-time Visualization**: Overlay detection results directly on the game window

### 🤖 Automation
- **Action Sequences**: Create and run sequences of actions:
  - Mouse clicks and movements
  - Keyboard input
  - Conditional logic and loops
  - Wait conditions
- **Task Scheduler**: Run sequences at specific times or intervals
- **Error Recovery**: Robust error handling with automatic recovery strategies

### 📊 Game State Tracking
- **Resource Monitoring**: Track game resources like gold, wood, and more
- **Map Analysis**: Visualize the game map and important elements
- **State History**: Record and analyze game state changes over time

### 🌐 Localization
- **Multi-language Interface**: Available in English and German with easy switching
- **Runtime Language Switching**: Change languages without restarting the application
- **Layout Adaptability**: UI automatically adjusts to accommodate different text lengths

### 🎨 User Experience
- **Modern Interface**: Clean, intuitive UI with tabbed organization
- **Theme System**: Light, dark, and system theme options
- **Keyboard Shortcuts**: Customizable shortcuts for efficient operation
- **Automatic Updates**: Built-in update system for seamless version upgrades

## Installation

### Pre-built Installers

Download the latest installers from the [Releases page](https://github.com/yourusername/scout/releases/tag/v1.0.0):

| Platform | File | Size | SHA-256 |
|----------|------|------|---------|
| Windows | [Scout_Setup_1.0.0.exe](https://github.com/yourusername/scout/releases/download/v1.0.0/Scout_Setup_1.0.0.exe) | 61.7 MB | 4ABD95D617FEDFA173990CDFF77101318AF781A4791E13E1A75530F0C0FD63D0 |
| Windows (Portable) | [Scout_1.0.0_Portable.zip](https://github.com/yourusername/scout/releases/download/v1.0.0/Scout_1.0.0_Portable.zip) | 89.0 MB | 93798EAF1D6079A85A17553D1A360FA32978EA843ECEA68395E4DFE17F4F5F34 |
| macOS | [Scout-1.0.0.dmg](https://github.com/yourusername/scout/releases/download/v1.0.0/Scout-1.0.0.dmg) | - | - |
| Linux | [scout-1.0.0.AppImage](https://github.com/yourusername/scout/releases/download/v1.0.0/scout-1.0.0.AppImage) | - | - |
| Linux (Debian) | [scout_1.0.0_amd64.deb](https://github.com/yourusername/scout/releases/download/v1.0.0/scout_1.0.0_amd64.deb) | - | - |

### System Requirements

- **Operating System**: Windows 10/11, macOS 11+, or Ubuntu 20.04+
- **Processor**: Dual-core CPU @ 2.0 GHz or better
- **Memory**: 4 GB RAM minimum, 8 GB recommended
- **Graphics**: DirectX 11 compatible graphics card
- **Display**: 1366x768 resolution minimum
- **Storage**: 500 MB available space
- **Internet**: Broadband internet connection for updates

### Installing from Source

#### Prerequisites
- Python 3.9, 3.10, or 3.11
- Qt libraries (automatically installed with PyQt6)
- For OCR: Tesseract OCR engine
- For YOLO detection: CUDA-compatible GPU (optional but recommended)

#### Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/yourusername/scout.git
cd scout
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python main.py
```

## Quick Start Guide

### 1. Initial Setup
- Launch Scout
- Select your game window from the detection window
- Configure basic settings in the Settings tab

### 2. Creating Detection Templates
- Go to the Detection tab
- Click "Capture Screenshot"
- Use the Template Creator to select game elements
- Save templates for future use

### 3. Creating Automation Sequences
- Go to the Automation tab
- Click "New Sequence"
- Add actions using the action editor (click, type, wait, etc.)
- Save and run your sequence

### 4. Monitoring Game State
- Go to the Game State tab to view resources and game information
- Track changes over time in the history view
- Export data for external analysis

## Documentation

Comprehensive documentation is available:

- [User Guide](docs/user_guide/README.md) - Complete guide for end users
- [Developer Documentation](docs/developer/README.md) - For developers extending Scout
- [API Reference](docs/api/README.md) - Detailed API documentation
- [Release Notes](docs/RELEASE_NOTES.md) - What's new in this version

## Architecture

Scout is built with a modular architecture following the SOLID principles:

- **Core**: Core services and business logic
  - **Window**: Window management and screen capture
  - **Detection**: Image analysis and object detection
  - **Game**: Game state tracking and analysis
  - **Automation**: Task scheduling and execution
  - **Events**: Event-based communication
  - **Design**: Design pattern implementations
  
- **UI**: User interface components
  - **Views**: Main application views
  - **Widgets**: Reusable UI components
  - **Dialogs**: Application dialogs
  - **Models**: Data models and storage
  - **Utils**: UI utility functions
  
- **Tools**: Development and utility tools
  - Build scripts
  - Testing utilities
  - Development tools

## Development

### Code Style

This project uses:
- Ruff for linting
- MyPy for type checking
- Pre-commit hooks for quality checks

```bash
# Run linting
ruff check .

# Run type checking
mypy scout
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest scout/tests/core
pytest scout/tests/ui
pytest scout/tests/integration
```

### Translation Workflow

To update or modify translations:

1. Update source strings in code:
```python
# Use tr() function or QObject.tr() method
label = QLabel(tr("Hello World"))
self.button.setText(self.tr("Click Me"))
```

2. Extract translatable strings:
```bash
pylupdate6 scout/**/*.py -ts scout/translations/scout_en.ts scout/translations/scout_de.ts
```

3. Edit translations using Qt Linguist or any text editor (XML format)

4. Compile translations:
```bash
lrelease scout/translations/scout_en.ts scout/translations/scout_de.ts
```

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for more information.

1. Fork the repository
2. Create a feature branch 
3. Make your changes
4. Run tests and ensure all checks pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- PyQt6 for the UI framework
- OpenCV for computer vision capabilities
- Tesseract for OCR functionality
- Ultralytics for YOLO implementation