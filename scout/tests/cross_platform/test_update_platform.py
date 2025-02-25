"""
Platform-Specific Update Tests

This module tests the platform-specific behaviors of the update system,
ensuring that the update checker, downloader, and installer work correctly
on different operating systems.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from scout.core.updater.update_checker import UpdateChecker
from scout.tests.cross_platform.platform_utils import (
    PlatformType,
    get_current_platform,
    PlatformContext,
    skip_on_platforms
)


class TestUpdateCheckerPlatformSpecific(unittest.TestCase):
    """Test platform-specific behaviors of the UpdateChecker class."""
    
    def setUp(self):
        """Set up each test case."""
        self.update_checker = UpdateChecker()
        self.dummy_installer = Path(os.path.join(os.path.dirname(__file__), "dummy_installer.exe"))
        
        # Create a dummy installer file for testing
        if not self.dummy_installer.exists():
            with open(self.dummy_installer, 'w') as f:
                f.write("Dummy installer file for testing")
    
    def tearDown(self):
        """Clean up after each test case."""
        # Remove the dummy installer if it exists
        if self.dummy_installer.exists():
            os.remove(self.dummy_installer)
    
    def test_platform_info_in_update_check(self):
        """Test that platform information is correctly included in update check requests."""
        with patch('urllib.request.urlopen') as mock_urlopen:
            # Mock the response
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"latest_version":"1.0.0"}'
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            # Capture the request data
            captured_request = None
            
            def side_effect(request, *args, **kwargs):
                nonlocal captured_request
                captured_request = request
                return mock_response
            
            mock_urlopen.side_effect = side_effect
            
            # Call the method
            self.update_checker.check_for_updates()
            
            # Verify request data contains platform info
            self.assertIsNotNone(captured_request)
            request_data = captured_request.data.decode('utf-8')
            self.assertIn(sys.platform, request_data)
            self.assertIn('"architecture":', request_data)
    
    def test_installer_launch_windows(self):
        """Test installer launch behavior on Windows."""
        # Skip this test on non-Windows platforms
        if skip_on_platforms((PlatformType.MACOS, PlatformType.LINUX)):
            self.skipTest("Test only applicable on Windows")
        
        with patch('subprocess.Popen') as mock_popen:
            # Mock the Popen call to avoid actually launching anything
            mock_popen.return_value = MagicMock()
            
            # Call the method
            result = self.update_checker.install_update(str(self.dummy_installer))
            
            # Verify the result and Popen call
            self.assertTrue(result)
            mock_popen.assert_called_once()
            
            # Verify creationflags for Windows
            args, kwargs = mock_popen.call_args
            self.assertIn('creationflags', kwargs)
    
    def test_installer_launch_simulated_platforms(self):
        """Test installer launch behavior on different platforms using simulation."""
        test_platforms = [
            PlatformType.WINDOWS,
            PlatformType.MACOS,
            PlatformType.LINUX
        ]
        
        # Try launching installer on each simulated platform
        for platform_type in test_platforms:
            with PlatformContext(platform_type), \
                 patch('subprocess.Popen') as mock_popen:
                
                # Mock the Popen call to avoid actually launching anything
                mock_popen.return_value = MagicMock()
                
                # Call the method
                result = self.update_checker.install_update(str(self.dummy_installer))
                
                # Verify the result
                self.assertTrue(result)
                mock_popen.assert_called_once()
                
                # Verify platform-specific Popen args
                args, kwargs = mock_popen.call_args
                
                if platform_type == PlatformType.WINDOWS:
                    self.assertIn('creationflags', kwargs)
                else:
                    self.assertNotIn('creationflags', kwargs)
    
    def test_installer_path_validation(self):
        """Test installer path validation works on all platforms."""
        # Test with a non-existent path
        non_existent_path = "non_existent_installer.exe"
        result = self.update_checker.install_update(non_existent_path)
        self.assertFalse(result)
        
        # Test with the dummy installer path
        result = self.update_checker.install_update(str(self.dummy_installer))
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main() 