"""
Translation Tools Configuration

This module contains configuration settings for the translation tools,
including common patterns, thresholds, and file types to process.
"""

from typing import Dict, List, Tuple, Pattern
import re

# Supported languages with their expansion factors relative to English
# English is the base (1.0), German is approximately 30% longer (1.3), etc.
LANGUAGE_EXPANSION_FACTORS: Dict[str, float] = {
    'en': 1.0,    # English (base)
    'de': 1.3,    # German (~30% longer)
    'fr': 1.2,    # French (~20% longer)
    'es': 1.15,   # Spanish (~15% longer)
    'it': 1.1,    # Italian (~10% longer)
    'ja': 0.6,    # Japanese (~40% shorter)
    'zh': 0.6,    # Chinese (~40% shorter)
    'ru': 1.2,    # Russian (~20% longer)
}

# Minimum width in pixels for common UI elements
MIN_WIDTHS: Dict[str, int] = {
    'button': 100,
    'label': 80,
    'input': 150,
    'combobox': 120,
    'checkbox': 130,
    'radio': 120,
}

# Long text threshold (characters)
LONG_TEXT_THRESHOLD: int = 30

# Default padding to add to calculated widths (pixels)
DEFAULT_PADDING: int = 20

# File types to process
UI_FILE_EXTENSIONS: List[str] = ['.py', '.ui']

# Directory exclusion patterns
EXCLUDED_DIRS: List[str] = ['__pycache__', '.git', 'venv', 'build', 'dist']

# Patterns to detect hardcoded strings
HARDCODED_STRING_PATTERNS: List[Pattern] = [
    # Look for QLabel with string literals
    re.compile(r"QLabel\([\"\'](.*?)[\"\']"),
    # Look for QPushButton with string literals
    re.compile(r"QPushButton\([\"\'](.*?)[\"\']"),
    # Look for setWindowTitle with string literals
    re.compile(r"setWindowTitle\([\"\'](.*?)[\"\']"),
    # Look for setText with string literals
    re.compile(r"setText\([\"\'](.*?)[\"\']"),
    # Look for title attributes with string literals
    re.compile(r"title\s*=\s*[\"\'](.*?)[\"\']"),
    # Look for string literals in menu creation
    re.compile(r"addMenu\([\"\'](.*?)[\"\']"),
    # Look for string literals in action creation
    re.compile(r"addAction\([\"\'](.*?)[\"\']"),
]

# Pattern to detect tr() calls
TR_PATTERN: Pattern = re.compile(r"(self\.tr|tr)\([\"\'](.*?)[\"\']")

# Patterns to detect potential layout issues
POTENTIAL_LAYOUT_ISSUE_PATTERN: Pattern = re.compile(
    r"(setFixedWidth|setFixedSize|setMinimumWidth|setMinimumSize)\([0-9]+"
)

# Font used for text measurement (family, size)
DEFAULT_FONT: Tuple[str, int] = ('Arial', 9)

# Default spacing values used in layouts
DEFAULT_SPACING: Dict[str, int] = {
    'horizontal': 6,
    'vertical': 6,
    'form': 8,
    'grid': 6,
    'margin': 9,
}

# Components that need special attention for layout issues
SENSITIVE_COMPONENTS: List[str] = [
    'TableView',
    'Dialog',
    'StatusBar',
    'MenuBar',
    'ToolBar',
    'ComboBox',
] 