"""
Platform Utilities

Utility functions and classes for cross-platform testing, providing
methods to detect the current platform, simulate different platforms,
and handle platform-specific behavior.
"""

import os
import sys
import platform
from enum import Enum, auto
from typing import Dict, Any, Tuple, Optional


class PlatformType(Enum):
    """Enumeration of supported platforms for testing."""
    WINDOWS = auto()
    MACOS = auto()
    LINUX = auto()
    UNKNOWN = auto()


def get_current_platform() -> PlatformType:
    """
    Detect and return the current platform type.
    
    Returns:
        PlatformType enum representing the current platform
    """
    if sys.platform.startswith('win'):
        return PlatformType.WINDOWS
    elif sys.platform.startswith('darwin'):
        return PlatformType.MACOS
    elif sys.platform.startswith('linux'):
        return PlatformType.LINUX
    else:
        return PlatformType.UNKNOWN


def get_platform_info() -> Dict[str, Any]:
    """
    Get detailed information about the current platform.
    
    Returns:
        Dictionary containing platform details
    """
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "platform_type": get_current_platform().name,
        "sys_platform": sys.platform,
    }


class PlatformContext:
    """
    Context manager for simulating different platforms during tests.
    
    This allows tests to simulate behavior on different platforms
    by temporarily modifying platform-related attributes.
    """
    
    def __init__(self, target_platform: PlatformType):
        """
        Initialize the platform context.
        
        Args:
            target_platform: The platform to simulate
        """
        self.target_platform = target_platform
        self.original_platform = None
        
    def __enter__(self) -> 'PlatformContext':
        """
        Enter the context by setting up the simulated platform.
        
        Returns:
            Self for context manager usage
        """
        # Store original platform info
        self.original_platform = sys.platform
        
        # Simulate target platform by patching sys.platform
        if self.target_platform == PlatformType.WINDOWS:
            sys.platform = 'win32'
        elif self.target_platform == PlatformType.MACOS:
            sys.platform = 'darwin'
        elif self.target_platform == PlatformType.LINUX:
            sys.platform = 'linux'
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context by restoring the original platform.
        """
        # Restore original platform
        sys.platform = self.original_platform


def skip_on_platforms(platforms: Tuple[PlatformType, ...]) -> bool:
    """
    Check if the current test should be skipped on specific platforms.
    
    Args:
        platforms: Tuple of platforms on which the test should be skipped
        
    Returns:
        True if the test should be skipped, False otherwise
    """
    current = get_current_platform()
    return current in platforms


def run_only_on_platforms(platforms: Tuple[PlatformType, ...]) -> bool:
    """
    Check if the current test should run only on specific platforms.
    
    Args:
        platforms: Tuple of platforms on which the test should run
        
    Returns:
        True if the test should run, False otherwise
    """
    current = get_current_platform()
    return current in platforms


def get_platform_specific_path(
    windows_path: str,
    macos_path: str,
    linux_path: str,
    unknown_path: Optional[str] = None
) -> str:
    """
    Get the appropriate path for the current platform.
    
    Args:
        windows_path: Path to use on Windows
        macos_path: Path to use on macOS
        linux_path: Path to use on Linux
        unknown_path: Path to use on unknown platforms
        
    Returns:
        Platform-appropriate path
    """
    platform_type = get_current_platform()
    
    if platform_type == PlatformType.WINDOWS:
        return windows_path
    elif platform_type == PlatformType.MACOS:
        return macos_path
    elif platform_type == PlatformType.LINUX:
        return linux_path
    else:
        return unknown_path if unknown_path is not None else windows_path  # Default to Windows path 