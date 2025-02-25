"""
Window Service Tests

This module contains unit tests for the WindowService class.
"""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from scout.core.window.window_service import WindowService
from scout.core.services.event_bus import EventBus

class TestWindowService(unittest.TestCase):
    """Tests for the WindowService class."""
    
    def setUp(self):
        """Set up tests."""
        self.event_bus = MagicMock(spec=EventBus)
        self.window_title = "Test Window"
        
        # Create WindowService with mocked dependencies
        with patch('scout.core.window.window_service.win32gui'), \
             patch('scout.core.window.window_service.win32con'), \
             patch('scout.core.window.window_service.ctypes'), \
             patch('scout.core.window.window_service.WindowCapture'):
                 
            self.service = WindowService(self.window_title, self.event_bus)
            
            # Mock the window_capture attribute
            self.service.window_capture = MagicMock()
            
            # Set some default values
            self.service.hwnd = 12345  # Fake window handle
            self.service._last_position = (100, 100, 800, 600)
            self.service._dpi_scale = 1.0
            self.service._client_offset_x = 8
            self.service._client_offset_y = 31
    
    def test_find_window_existing_window(self):
        """Test finding window when handle already exists."""
        # Mock IsWindow to return True and GetWindowText to return the title
        with patch('scout.core.window.window_service.win32gui.IsWindow', return_value=True), \
             patch('scout.core.window.window_service.win32gui.GetWindowText', return_value=self.window_title):
                 
            result = self.service.find_window()
            self.assertTrue(result)
    
    def test_find_window_new_window(self):
        """Test finding a new window."""
        # Reset window handle
        self.service.hwnd = None
        
        # Mock EnumWindows to call the callback with a matching window
        def mock_enum_windows(callback, _):
            callback(12345, None)  # Call with fake hwnd
            
        # Mock window title and visibility checks
        with patch('scout.core.window.window_service.win32gui.EnumWindows', side_effect=mock_enum_windows), \
             patch('scout.core.window.window_service.win32gui.IsWindowVisible', return_value=True), \
             patch('scout.core.window.window_service.win32gui.GetWindowText', return_value=self.window_title), \
             patch.object(self.service, '_update_window_metrics'), \
             patch.object(self.service, '_publish_window_changed_event'):
                 
            result = self.service.find_window()
            self.assertTrue(result)
            self.assertEqual(self.service.hwnd, 12345)
    
    def test_get_window_position(self):
        """Test getting window position."""
        # Mock win32gui.GetWindowRect to return a fake rectangle
        with patch('scout.core.window.window_service.win32gui.GetWindowRect', return_value=(100, 100, 900, 700)), \
             patch.object(self.service, 'find_window', return_value=True), \
             patch.object(self.service, '_publish_window_changed_event'):
                 
            position = self.service.get_window_position()
            self.assertEqual(position, (100, 100, 800, 600))
    
    def test_capture_screenshot(self):
        """Test capturing a screenshot."""
        # Create a fake screenshot
        fake_screenshot = np.zeros((600, 800, 3), dtype=np.uint8)
        
        # Mock necessary methods
        with patch.object(self.service, 'find_window', return_value=True), \
             patch.object(self.service, 'get_window_position', return_value=(100, 100, 800, 600)), \
             patch.object(self.service.window_capture, 'capture', return_value=fake_screenshot):
                 
            screenshot = self.service.capture_screenshot()
            
            # Check if screenshot was captured
            self.assertIsNotNone(screenshot)
            self.assertEqual(screenshot.shape, (600, 800, 3))
            
            # Check if events were emitted
            self.service.screenshot_captured.emit.assert_called_once()
            self.event_bus.publish.assert_called_once()
    
    def test_client_to_screen(self):
        """Test converting client coordinates to screen coordinates."""
        # Mock necessary methods
        with patch.object(self.service, 'find_window', return_value=True), \
             patch.object(self.service, 'get_window_position', return_value=(100, 100, 800, 600)):
                 
            # Test conversion (client coordinates 50,50 -> screen coordinates)
            screen_coords = self.service.client_to_screen(50, 50)
            
            # Expected: client + window position + client offset
            expected = (50 + 100 + self.service._client_offset_x, 
                      50 + 100 + self.service._client_offset_y)
            
            self.assertEqual(screen_coords, expected)
    
    def test_screen_to_client(self):
        """Test converting screen coordinates to client coordinates."""
        # Mock necessary methods
        with patch.object(self.service, 'find_window', return_value=True), \
             patch.object(self.service, 'get_window_position', return_value=(100, 100, 800, 600)):
                 
            # Window at (100,100), client offset (8,31)
            # For screen coordinates (158,181), client should be (50,50)
            screen_x = 100 + self.service._client_offset_x + 50
            screen_y = 100 + self.service._client_offset_y + 50
            
            client_coords = self.service.screen_to_client(screen_x, screen_y)
            expected = (50, 50)
            
            self.assertEqual(client_coords, expected)

if __name__ == '__main__':
    unittest.main() 