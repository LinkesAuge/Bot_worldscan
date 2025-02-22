# TB Scout

A Python application for automating interactions with the Total Battle browser game through computer vision and automation.

## Features

- Window detection and tracking for both standalone and browser versions
- Screenshot capture and analysis
- Pattern matching for game elements
- OCR text extraction from game elements
- Mouse and keyboard automation
- Debug visualization and logging
- Sound notifications

## Requirements

- Python 3.9 or higher
- Tesseract OCR 5.5
- Windows 10/11

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tb_scout.git
cd tb_scout
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install development dependencies (optional):
```bash
pip install -r requirements-dev.txt
pip install -r requirements-test.txt
```

5. Install Tesseract OCR:
```bash
choco install tesseract
```

## Project Structure

```
tb_scout/
├── scout/                 # Main package directory
│   ├── core/             # Core functionality
│   ├── capture/          # Screen capture and analysis
│   ├── gui/              # GUI components
│   │   └── widgets/      # Custom widgets
│   └── visualization/    # Debug visualization
├── tests/                # Test suite
├── images/              # Pattern matching templates
├── sounds/              # Notification sounds
├── debug_screenshots/   # Debug output
└── logs/               # Application logs
```

## Development

### Setting up the development environment

1. Install pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

2. Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Running Tests

Run the full test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=scout
```

Generate coverage report:
```bash
pytest --cov=scout --cov-report=html
```

### Code Quality

The project uses several tools to maintain code quality:

- **Ruff**: For linting and code formatting
- **MyPy**: For static type checking
- **Pytest**: For testing
- **Coverage.py**: For code coverage tracking
- **Pre-commit**: For automated checks before commits

Run linting:
```bash
ruff check .
```

Run type checking:
```bash
mypy scout
```

### Continuous Integration

The project uses GitHub Actions for CI/CD:

- Runs tests on Windows with Python 3.9, 3.10, and 3.11
- Performs linting and type checking
- Generates test coverage reports
- Builds executable

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and ensure all checks pass
5. Submit a pull request

### Commit Message Format

Use the following prefixes for commit messages:

- `fix:` for bug fixes
- `feat:` for new features
- `perf:` for performance improvements
- `ui:` for GUI/UI changes
- `style:` for formatting changes
- `log:` for logs/debugging related changes
- `docs:` for documentation changes
- `refactor:` for code refactoring
- `test:` for adding missing tests
- `other:` for any other changes

## License

MIT License - see LICENSE file for details
