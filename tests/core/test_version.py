"""Tests for the version module."""

from unittest.mock import patch
from scout.version import (
    __version__,
    __author__,
    __license__,
    VERSION,
    VERSION_INFO,
    IS_RELEASED,
    GIT_REVISION,
    get_version_string
)

def test_version_attributes() -> None:
    """Test that version attributes are properly defined."""
    assert isinstance(__version__, str)
    assert isinstance(__author__, str)
    assert isinstance(__license__, str)
    assert isinstance(VERSION, str)
    assert isinstance(VERSION_INFO, tuple)
    assert isinstance(IS_RELEASED, bool)
    assert isinstance(GIT_REVISION, str)

def test_version_info_format() -> None:
    """Test that VERSION_INFO is a tuple of three integers."""
    assert len(VERSION_INFO) == 3
    assert all(isinstance(x, int) for x in VERSION_INFO)

def test_version_string_matches_info() -> None:
    """Test that VERSION string matches VERSION_INFO tuple."""
    expected = ".".join(str(x) for x in VERSION_INFO)
    assert VERSION == expected

def test_get_version_string_released():
    """Test getting version string for released version."""
    with patch('scout.version.IS_RELEASED', True), \
         patch('scout.version.GIT_REVISION', 'abcdef123'):
        version_string = get_version_string()
        assert version_string == VERSION, f"Expected '{VERSION}' but got '{version_string}'"

def test_get_version_string_unreleased():
    """Test getting version string for unreleased version."""
    with patch('scout.version.IS_RELEASED', False), \
         patch('scout.version.GIT_REVISION', 'abcdef123'):
        version_string = get_version_string()
        expected = f"{VERSION}+dev.abcdef1"
        assert version_string == expected, f"Expected '{expected}' but got '{version_string}'"

def test_license_is_mit() -> None:
    """Test that the license is MIT."""
    assert __license__ == "MIT"

def test_author_is_set() -> None:
    """Test that the author is set."""
    assert __author__ == "TB Scout Contributors"

def test_version_info():
    """Test version info tuple."""
    assert len(VERSION_INFO) == 3
    assert all(isinstance(x, int) for x in VERSION_INFO)
    assert VERSION == ".".join(str(x) for x in VERSION_INFO)

def test_metadata():
    """Test version metadata."""
    assert isinstance(__version__, str)
    assert isinstance(__author__, str)
    assert isinstance(__license__, str) 