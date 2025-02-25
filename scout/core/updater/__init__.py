"""
Scout Updater Package

This package provides functionality for checking, downloading, and installing
application updates. It includes both backend logic and user interface components.
"""

from scout.core.updater.update_checker import get_update_checker
from scout.core.updater.settings import get_update_settings
from scout.ui.dialogs.update_dialog import show_update_dialog, check_for_updates_in_background

__all__ = [
    'get_update_checker',
    'get_update_settings',
    'show_update_dialog',
    'check_for_updates_in_background'
] 