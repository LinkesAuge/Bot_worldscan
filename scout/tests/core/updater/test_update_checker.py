"""
Update Checker Tests

This module contains tests for the update checker functionality.
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

# Ensure the scout package is in the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent.parent.parent
if project_root not in sys.path:
    sys.path.insert(0, str(project_root))

from scout.core.updater.update_checker import UpdateChecker, get_update_checker, CURRENT_VERSION


class TestUpdateChecker(unittest.TestCase):
    """Tests for the UpdateChecker class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a test update checker with a mock URL
        self.test_url = "https://test.example.com/updates"
        self.update_checker = UpdateChecker(current_version="1.0.0", update_url=self.test_url)
        
        # Sample update data for mocking
        self.sample_update_data = {
            "latest_version": "1.0.1",
            "download_url": "https://example.com/downloads/Scout_Setup_1.0.1.exe",
            "update_info": "Test update",
            "changelog": "<ul><li>Test changes</li></ul>"
        }
    
    def tearDown(self):
        """Clean up after tests."""
        pass
    
    @patch('scout.core.updater.update_checker.urlopen')
    def test_check_for_updates_newer_version(self, mock_urlopen):
        """Test checking for updates when a newer version is available."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(self.sample_update_data).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Check for updates
        result = self.update_checker.check_for_updates()
        
        # Verify result
        self.assertTrue(result)
        self.assertEqual(self.update_checker.latest_version, "1.0.1")
        self.assertEqual(self.update_checker.download_url, self.sample_update_data["download_url"])
        self.assertEqual(self.update_checker.update_info, self.sample_update_data["update_info"])
        self.assertEqual(self.update_checker.changelog, self.sample_update_data["changelog"])
    
    @patch('scout.core.updater.update_checker.urlopen')
    def test_check_for_updates_same_version(self, mock_urlopen):
        """Test checking for updates when the current version is the latest."""
        # Update the sample data to match current version
        update_data = self.sample_update_data.copy()
        update_data["latest_version"] = "1.0.0"  # Same as current
        
        # Mock the response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(update_data).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Check for updates
        result = self.update_checker.check_for_updates()
        
        # Verify result
        self.assertFalse(result)  # No update available
        self.assertEqual(self.update_checker.latest_version, "1.0.0")
    
    @patch('scout.core.updater.update_checker.urlopen')
    def test_check_for_updates_older_version(self, mock_urlopen):
        """Test checking for updates when the current version is newer than the 'latest'."""
        # Set the current version to something newer
        self.update_checker.current_version = "2.0.0"
        
        # Mock the response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(self.sample_update_data).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Check for updates
        result = self.update_checker.check_for_updates()
        
        # Verify result
        self.assertFalse(result)  # No update available
    
    @patch('scout.core.updater.update_checker.urlopen')
    def test_check_for_updates_connection_error(self, mock_urlopen):
        """Test checking for updates when connection fails."""
        # Mock the urlopen function to raise an exception
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Connection error")
        
        # Check for updates
        result = self.update_checker.check_for_updates()
        
        # Verify result
        self.assertFalse(result)
        self.assertIsNone(self.update_checker.latest_version)
    
    @patch('scout.core.updater.update_checker.urlopen')
    def test_download_update_success(self, mock_urlopen):
        """Test downloading an update successfully."""
        # Set up test data
        self.update_checker.download_url = "https://example.com/downloads/test.exe"
        
        # Create a temporary file
        temp_dir = tempfile.mkdtemp()
        
        # Mock the response with some dummy data
        mock_response = MagicMock()
        mock_response.read.side_effect = [b"test", b"data", b""]  # Return some data, then empty to end the loop
        mock_response.getheader.return_value = "8"  # Content length
        
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Download the update
        result = self.update_checker.download_update(temp_dir)
        
        # Verify the result is a path
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, str))
        
        # Clean up
        if os.path.exists(result):
            os.remove(result)
        os.rmdir(temp_dir)
    
    def test_download_update_no_url(self):
        """Test downloading an update when no download URL is available."""
        # Reset download URL
        self.update_checker.download_url = None
        
        # Try to download
        result = self.update_checker.download_update()
        
        # Verify result is None
        self.assertIsNone(result)
    
    @patch('scout.core.updater.update_checker.urlopen')
    def test_download_update_connection_error(self, mock_urlopen):
        """Test downloading an update when connection fails."""
        # Set up test data
        self.update_checker.download_url = "https://example.com/downloads/test.exe"
        
        # Mock the urlopen function to raise an exception
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Connection error")
        
        # Try to download
        result = self.update_checker.download_update()
        
        # Verify result is None
        self.assertIsNone(result)
    
    @patch('scout.core.updater.update_checker.subprocess.Popen')
    def test_install_update_success(self, mock_popen):
        """Test installing an update successfully."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test installer data")
            installer_path = temp_file.name
        
        # Mock successful process creation
        mock_popen.return_value = MagicMock()
        
        # Install the update
        result = self.update_checker.install_update(installer_path)
        
        # Verify result is True
        self.assertTrue(result)
        
        # Check that Popen was called with the correct arguments
        if sys.platform == 'win32':
            mock_popen.assert_called()
        
        # Clean up
        os.unlink(installer_path)
    
    def test_install_update_file_not_found(self):
        """Test installing an update when the installer file is not found."""
        # Use a non-existent file path
        installer_path = "/path/to/nonexistent/file.exe"
        
        # Try to install
        result = self.update_checker.install_update(installer_path)
        
        # Verify result is False
        self.assertFalse(result)
    
    @patch('scout.core.updater.update_checker.subprocess.Popen')
    def test_install_update_error(self, mock_popen):
        """Test installing an update when process creation fails."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test installer data")
            installer_path = temp_file.name
        
        # Mock process creation to raise an exception
        mock_popen.side_effect = OSError("Process error")
        
        # Try to install
        result = self.update_checker.install_update(installer_path)
        
        # Verify result is False
        self.assertFalse(result)
        
        # Clean up
        os.unlink(installer_path)
    
    def test_compare_versions(self):
        """Test version comparison."""
        # Test equal versions
        self.assertEqual(self.update_checker._compare_versions("1.0.0", "1.0.0"), 0)
        
        # Test newer version
        self.assertEqual(self.update_checker._compare_versions("1.0.0", "1.0.1"), -1)
        self.assertEqual(self.update_checker._compare_versions("1.0.0", "1.1.0"), -1)
        self.assertEqual(self.update_checker._compare_versions("1.0.0", "2.0.0"), -1)
        
        # Test older version
        self.assertEqual(self.update_checker._compare_versions("1.0.1", "1.0.0"), 1)
        self.assertEqual(self.update_checker._compare_versions("1.1.0", "1.0.0"), 1)
        self.assertEqual(self.update_checker._compare_versions("2.0.0", "1.0.0"), 1)
        
        # Test versions with different lengths
        self.assertEqual(self.update_checker._compare_versions("1.0", "1.0.0"), 0)
        self.assertEqual(self.update_checker._compare_versions("1.0.0.0", "1.0.0"), 0)
        self.assertEqual(self.update_checker._compare_versions("1.0", "1.0.1"), -1)
        self.assertEqual(self.update_checker._compare_versions("1.0.1", "1.0"), 1)
    
    def test_get_update_info(self):
        """Test getting update information."""
        # Set update information
        self.update_checker.current_version = "1.0.0"
        self.update_checker.latest_version = "1.0.1"
        self.update_checker.download_url = "https://example.com/downloads/test.exe"
        self.update_checker.update_info = "Test update"
        self.update_checker.changelog = "<ul><li>Test changes</li></ul>"
        
        # Get update info
        info = self.update_checker.get_update_info()
        
        # Verify info
        self.assertEqual(info["current_version"], "1.0.0")
        self.assertEqual(info["latest_version"], "1.0.1")
        self.assertTrue(info["update_available"])
        self.assertEqual(info["download_url"], "https://example.com/downloads/test.exe")
        self.assertEqual(info["update_info"], "Test update")
        self.assertEqual(info["changelog"], "<ul><li>Test changes</li></ul>")
    
    def test_get_update_info_no_update(self):
        """Test getting update information when no update is available."""
        # Set update information with same version
        self.update_checker.current_version = "1.0.0"
        self.update_checker.latest_version = "1.0.0"
        
        # Get update info
        info = self.update_checker.get_update_info()
        
        # Verify update is not available
        self.assertFalse(info["update_available"])
    
    def test_get_update_checker_singleton(self):
        """Test that get_update_checker returns a singleton instance."""
        # Get the update checker instance
        checker1 = get_update_checker()
        checker2 = get_update_checker()
        
        # Verify both instances are the same object
        self.assertIs(checker1, checker2)
        
        # Verify it's an UpdateChecker instance
        self.assertIsInstance(checker1, UpdateChecker)
        
        # Verify it uses the default version and URL
        self.assertEqual(checker1.current_version, CURRENT_VERSION)


if __name__ == "__main__":
    unittest.main() 