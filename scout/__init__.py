"""TB Scout - Total Battle Game Assistant.

A Python application for automating interactions with the Total Battle browser game
through computer vision and automation.
"""

from typing import Final

from .version import (
    __version__,
    __author__,
    __license__,
    VERSION,
    VERSION_INFO,
    IS_RELEASED,
    GIT_REVISION,
    get_version_string,
)

# Application constants
APP_NAME: Final[str] = "TB Scout"
APP_DESCRIPTION: Final[str] = "Total Battle Game Assistant"
APP_ORGANIZATION: Final[str] = "TB Scout"
APP_DOMAIN: Final[str] = "tbscout.local"

# Window detection constants
WINDOW_TITLE_STANDALONE: Final[str] = "Total Battle"
WINDOW_TITLE_BROWSER: Final[str] = "Total Battle - "  # Browser title prefix

# File paths
CONFIG_FILE: Final[str] = "config.ini"
LOG_DIR: Final[str] = "logs"
DEBUG_SCREENSHOTS_DIR: Final[str] = "debug_screenshots"
IMAGES_DIR: Final[str] = "images"
SOUNDS_DIR: Final[str] = "sounds"

# Import commonly used submodules
from .core import *  # noqa: F403
from .capture import *  # noqa: F403
from .gui import *  # noqa: F403
from .visualization import *  # noqa: F403

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "VERSION",
    "VERSION_INFO",
    "IS_RELEASED",
    "GIT_REVISION",
    "get_version_string",
    "APP_NAME",
    "APP_DESCRIPTION",
    "APP_ORGANIZATION",
    "APP_DOMAIN",
    "WINDOW_TITLE_STANDALONE",
    "WINDOW_TITLE_BROWSER",
    "CONFIG_FILE",
    "LOG_DIR",
    "DEBUG_SCREENSHOTS_DIR",
    "IMAGES_DIR",
    "SOUNDS_DIR",
]
