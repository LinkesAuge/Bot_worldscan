"""
Cross-Platform Testing Module

This module contains tests to verify that the Scout application
works correctly across different operating systems and environments.

Tests in this module check platform-specific code paths and verify
that the application behavior is consistent across platforms.
"""

from scout.tests.cross_platform.platform_utils import get_current_platform, PlatformType

__all__ = ["get_current_platform", "PlatformType"] 