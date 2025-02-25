# Scout - Game Automation and Detection Tool

Scout is a powerful automation and computer vision tool designed to detect and interact with game elements, automate repetitive tasks, and analyze game state. Version 1.0.0 is now available with full multilingual support, error recovery, and cross-platform compatibility.

## Features

- **Game Window Detection**: Automatically finds and tracks the game window
- **Computer Vision**: Supports template matching, OCR, and YOLO object detection
- **Automation**: Create and run sequences of actions (click, type, wait, etc.)
- **Game State Tracking**: Monitor and record game state changes over time
- **Real-time Visualization**: Overlay detection results on the game window
- **Extensible Architecture**: Modular design with clean interfaces
- **Multi-language Support**: Available in English and German with easy switching
- **Automatic Updates**: Built-in update system for seamless version upgrades
- **Error Recovery**: Robust error handling with automatic recovery strategies
- **Cross-platform**: Fully tested on Windows, macOS, and Linux

## Installation

### Pre-built Installers

Download the latest installers from the [Releases page](https://github.com/yourusername/scout/releases/tag/v1.0.0):

- **Windows**: Scout_Setup_1.0.0.exe
- **macOS**: Scout-1.0.0.dmg
- **Linux**: scout-1.0.0.AppImage or scout_1.0.0_amd64.deb

The installers include all required dependencies, including Python and required libraries.

### Prerequisites (for installing from source)

- Python 3.9, 3.10, or 3.11
- Qt libraries (automatically installed with PyQt6)
- For OCR: Tesseract OCR engine
- For YOLO detection: CUDA-compatible GPU (optional but recommended)

### Installing from Source

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

## What's New in 1.0.0

The 1.0.0 release includes numerous improvements and new features:

- **Multi-language Support**: Complete English and German translations
- **Theme System**: Light, dark, and system theme options
- **Keyboard Shortcuts**: Customizable shortcuts for efficient operation
- **Error Reporting and Recovery**: Robust error handling with recovery strategies
- **Cross-platform Compatibility**: Fully tested on Windows, macOS, and Linux
- **Performance Optimizations**: Faster detection and improved memory usage
- **Comprehensive Documentation**: Complete user and developer guides

For a complete list of changes, see the [Release Notes](docs/RELEASE_NOTES.md) and [What's New](docs/user_guide/whats_new.md) guide.

## Usage

### Basic Operation

1. Start the application
2. Select your game window from the window selection dialog
3. Use the Detection tab to find game elements
4. Use the Automation tab to create and run sequences
5. Use the Game State tab to monitor game variables

### Creating Detection Templates

1. Capture a screenshot of the game
2. Open the Template Creator
3. Select the elements you want to detect
4. Save the templates

### Creating Automation Sequences

1. Go to the Automation tab
2. Click "New Sequence"
3. Add actions to the sequence (click, type, wait, etc.)
4. Configure each action's properties
5. Save the sequence
6. Click "Run" to execute the sequence

### Monitoring Game State

1. Go to the Game State tab
2. Add state variables to track
3. Set up state transitions based on detection results
4. View the state history to track changes over time

### Changing Language Settings

1. Go to the Settings tab
2. Select the "UI" section
3. Choose your preferred language from the dropdown (English or German)
4. The application will immediately switch to the selected language
5. Some components may require an application restart to fully update

## Architecture

Scout is built with a modular architecture following the MVC pattern:

- **Core**: Contains core services and business logic
  - **Window**: Window management and screen capture
  - **Detection**: Image analysis and object detection
  - **Game**: Game state tracking and analysis
  - **Automation**: Task scheduling and execution
- **UI**: User interface components
  - **Controllers**: Application logic
  - **Models**: Data models
  - **Views**: UI views
  - **Widgets**: Reusable UI components
- **Localization**: Internationalization components
  - **LanguageManager**: Manages language switching and persistence
  - **Translations**: Language resource files

## Development

### Project Structure

```
scout/
├── core/          # Core functionality
├── ui/            # User interface
│   ├── utils/
│   │   ├── language_manager.py  # Language management system
├── resources/     # Application resources
├── translations/  # Language files
│   ├── scout_en.ts  # English translation source
│   ├── scout_en.qm  # Compiled English translation
│   ├── scout_de.ts  # German translation source
│   └── scout_de.qm  # Compiled German translation
├── tests/         # Test suite
├── main.py        # Application entry point
└── requirements.txt  # Dependencies
```

### Running Tests

```bash
pytest
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

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- PyQt6 for the UI framework
- OpenCV for computer vision capabilities
- Tesseract for OCR functionality
- Ultralytics for YOLO implementation