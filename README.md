# Scout - Game Automation and Detection Tool

Scout is a powerful automation and computer vision tool designed to detect and interact with game elements, automate repetitive tasks, and analyze game state.

## Features

- **Game Window Detection**: Automatically finds and tracks the game window
- **Computer Vision**: Supports template matching, OCR, and YOLO object detection
- **Automation**: Create and run sequences of actions (click, type, wait, etc.)
- **Game State Tracking**: Monitor and record game state changes over time
- **Real-time Visualization**: Overlay detection results on the game window
- **Extensible Architecture**: Modular design with clean interfaces

## Installation

### Prerequisites

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

## Development

### Project Structure

```
scout/
├── core/          # Core functionality
├── ui/            # User interface
├── resources/     # Application resources
├── tests/         # Test suite
├── main.py        # Application entry point
└── requirements.txt  # Dependencies
```

### Running Tests

```bash
pytest
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