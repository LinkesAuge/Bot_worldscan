# Contributing to Scout

Thank you for your interest in contributing to Scout! This document provides guidelines and instructions for contributing to the project.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Environment](#development-environment)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Documentation](#documentation)
- [Translation Guidelines](#translation-guidelines)
- [Release Process](#release-process)

## Code of Conduct

This project and everyone participating in it is governed by the Scout Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
   ```bash
   git clone https://github.com/YOUR_USERNAME/scout.git
   cd scout
   ```
3. **Set up the development environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```
4. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

## How to Contribute

There are many ways to contribute to Scout:

- **Report bugs**: Submit issues for any bugs you encounter
- **Suggest features**: Submit issues for feature requests
- **Fix bugs**: Look through the issue tracker for bugs that need fixing
- **Implement features**: Pick up feature requests from the issue tracker
- **Improve documentation**: Help improve or translate documentation
- **Add translations**: Help translate the application into more languages
- **Review pull requests**: Help review and test pull requests from other contributors

## Development Environment

Scout is developed with Python using the following tools:

- **Python**: 3.9, 3.10, or 3.11
- **IDE**: Any IDE with good Python support (VS Code, PyCharm, etc.)
- **Version Control**: Git
- **Package Management**: pip
- **Testing**: pytest
- **Linting**: ruff
- **Type Checking**: mypy
- **Pre-commit**: Various code quality hooks

### Configuring IDE

For VS Code, we recommend the following extensions:
- Python extension
- Pylance for static type checking
- Ruff for linting
- GitLens for enhanced Git capabilities

## Coding Standards

We follow PEP 8 and other Python best practices:

- Use 4 spaces for indentation
- Maximum line length is 88 characters (following Black's default)
- Use clear, descriptive variable and function names
- Write docstrings for all functions, classes, and modules
- Use type hints consistently
- Prefer composition over inheritance
- Follow the SOLID principles

### Code Organization

- Keep functions and methods small and focused
- Organize related functionality into modules
- Follow the project's architecture (core services, UI components, etc.)
- Use appropriate design patterns but avoid over-engineering

## Testing Guidelines

All code should be covered by tests:

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test interactions between components
- **UI Tests**: Test the user interface functionality
- **End-to-End Tests**: Test complete user workflows

### Writing Tests

- Tests should be in the `scout/tests` directory
- Test files should be named `test_*.py`
- Use pytest fixtures for test setup and teardown
- Mock external dependencies and services
- Test both success and failure scenarios

### Running Tests

```bash
# Run all tests
pytest

# Run specific tests
pytest scout/tests/core
pytest scout/tests/ui
pytest -k "test_specific_function"

# Run with coverage
pytest --cov=scout

# Generate coverage report
pytest --cov=scout --cov-report=html
```

## Commit Guidelines

We follow the conventional commits specification:

- **fix**: A bug fix
- **feat**: A new feature
- **perf**: A performance improvement
- **ui**: Changes to the UI
- **style**: Code style changes (formatting, etc.)
- **log**: Changes to logging
- **docs**: Documentation changes
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **other**: Other changes

Example commit messages:
```
feat: add German translation support
fix: correct initialization of WindowService
refactor: reorganize detection module for better separation of concerns
docs: update API documentation for automation service
```

## Pull Request Process

1. **Create a branch** from `main` with a descriptive name
   ```bash
   git checkout -b fix-settings-tab-initialization
   ```
2. **Make your changes** following the coding standards
3. **Run tests** to ensure they pass
   ```bash
   pytest
   ```
4. **Run linting and type checking** to ensure code quality
   ```bash
   ruff check .
   mypy scout
   ```
5. **Commit your changes** following the commit guidelines
6. **Push your branch** to your fork
   ```bash
   git push origin fix-settings-tab-initialization
   ```
7. **Create a pull request** to the `main` branch of the original repository
8. **Describe your changes** in the pull request description
9. **Wait for review** and address any feedback

## Documentation

We value comprehensive documentation:

- **Code Documentation**: All code should be documented with docstrings
- **User Guide**: Updates to features should include user guide updates
- **API Documentation**: Public APIs should have complete API documentation
- **Examples**: Include examples for complex functionality

### Docstring Format

We use Google-style docstrings:

```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """Short description of the function.
    
    More detailed description of the function's behavior.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: When the exception is raised
        
    Examples:
        >>> function_name("example", 123)
        "result"
    """
```

## Translation Guidelines

Scout is designed to be multilingual, with current support for English and German:

### Adding Translations

1. Mark strings for translation in code:
```python
# Function-based translation
from scout.ui.utils.language_manager import tr
label = QLabel(tr("Hello World"))

# Method-based translation
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

### Translation Tips

- Consider context when translating (same English word might translate differently in different contexts)
- Be aware of text expansion (German can be 20-30% longer than English)
- Test the UI with your translations to ensure proper layout
- Use proper capitalization and formatting for the target language

## Release Process

Scout follows semantic versioning (MAJOR.MINOR.PATCH):

1. **Prepare Release**
   - Update version number in `scout/__init__.py`
   - Update changelog in `docs/RELEASE_NOTES.md`
   - Update `docs/user_guide/whats_new.md`
   - Ensure all tests pass on all supported platforms
   
2. **Build Release**
   - Run the release preparation script
   ```bash
   python tools/prepare_release.py
   ```
   
3. **Publish Release**
   - Create a GitHub release with release notes
   - Upload built artifacts
   - Tag the release in Git
   
4. **Post-Release**
   - Announce the release on relevant channels
   - Monitor for any issues
   - Begin planning for the next release

Thank you for contributing to Scout!