"""Version information for TB Scout."""

from typing import Final, Tuple

__version__: Final[str] = "0.1.0"
__author__: Final[str] = "TB Scout Contributors"
__license__: Final[str] = "MIT"
__copyright__: Final[str] = "Copyright 2024 TB Scout Contributors"

# Version information tuple
VERSION_INFO: Final[Tuple[int, int, int]] = tuple(
    int(i) for i in __version__.split(".")[:3]
)

# String formatted version
VERSION: Final[str] = ".".join(str(i) for i in VERSION_INFO)

# Development status
IS_RELEASED: bool = False

# Git revision
GIT_REVISION: str = "Unknown"

def get_version_string() -> str:
    """Get the full version string.
    
    Returns:
        str: Full version string including git revision if available.
    """
    if not IS_RELEASED:
        return f"{VERSION}+dev.{GIT_REVISION[:7]}"
    return VERSION 