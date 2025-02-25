"""
DetectionService and GameService Integration Tests

This module contains integration tests that verify the interaction between
the DetectionService and GameService components.
"""

import unittest
import os
import tempfile
import json
import shutil
import cv2
import numpy as np
from unittest.mock import MagicMock, patch

from scout.core.events.event_bus import EventBus
from scout.core.events.event_types import EventType
from scout.core.window.window_service import WindowService
from scout.core.detection.detection_service import DetectionService
from scout.core.detection.strategies.template_strategy import TemplateMatchingStrategy
from scout.core.detection.strategies.ocr_strategy import OCRStrategy
from scout.core.game.game_service import GameService
from scout.core.game.game_state import Coordinates

class TestDetectionGameIntegration(unittest.TestCase):
    """
    Integration tests for DetectionService and GameService.
    
    These tests verify that:
    1. GameService can use DetectionService to extract game information
    2. GameService can correctly update game state based on detection results
    3. Events are properly published between the components
    """
    
    def setUp(self):
        """Set up test fixture."""
        # Create event bus
        self.event_bus = EventBus()
        
        # Set up event listener to track events
        self.received_events = []
        self.event_bus.subscribe(EventType.GAME_STATE_CHANGED, self._on_game_event)
        
        # Create temporary directory for templates and cache
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = os.path.join(self.temp_dir, 'templates')
        self.state_dir = os.path.join(self.temp_dir, 'state')
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.state_dir, exist_ok=True)
        
        # Create test template images
        self._create_test_templates()
        
        # Create a mock window service
        self.window_service = self._create_mock_window_service()
        
        # Create detection service with strategies
        self.detection_service = self._create_detection_service()
        
        # Create game service
        self.game_service = GameService(
            self.event_bus,
            self.detection_service,
            state_file_path=os.path.join(self.state_dir, 'game_state.json')
        )
    
    def tearDown(self):
        """Clean up after the test."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def _on_game_event(self, event):
        """Store received game state events for later verification."""
        self.received_events.append(event)
    
    def _create_test_templates(self):
        """Create test template images for detection."""
        # Create resource template (gold coin)
        gold_path = os.path.join(self.templates_dir, 'gold_resource.png')
        gold_img = np.zeros((40, 40, 3), dtype=np.uint8)
        gold_img[:, :] = [0, 215, 255]  # BGR for gold color
        cv2.circle(gold_img, (20, 20), 15, (0, 165, 255), -1)  # Darker gold circle
        cv2.imwrite(gold_path, gold_img)
        
        # Create building template (castle)
        castle_path = os.path.join(self.templates_dir, 'castle.png')
        castle_img = np.zeros((60, 60, 3), dtype=np.uint8)
        castle_img[:, :] = [90, 90, 90]  # Gray background
        # Simple castle shape
        cv2.rectangle(castle_img, (10, 30), (50, 59), (50, 50, 120), -1)  # Base
        cv2.rectangle(castle_img, (20, 10), (40, 30), (50, 50, 120), -1)  # Top
        cv2.imwrite(castle_path, castle_img)
    
    def _create_mock_window_service(self):
        """Create a mock window service with test screenshots."""
        window_service = WindowService(self.event_bus)
        
        # Create a game screenshot with gold and castle
        game_image = np.zeros((400, 600, 3), dtype=np.uint8)
        
        # Add gold resource at position (100, 100)
        gold_region = game_image[100:140, 100:140]
        gold_region[:, :] = [0, 215, 255]  # BGR for gold color
        cv2.circle(gold_region, (20, 20), 15, (0, 165, 255), -1)
        
        # Add castle at position (300, 200)
        castle_region = game_image[200:260, 300:360]
        castle_region[:, :] = [90, 90, 90]  # Gray background
        cv2.rectangle(castle_region, (10, 30), (50, 59), (50, 50, 120), -1)
        cv2.rectangle(castle_region, (20, 10), (40, 30), (50, 50, 120), -1)
        
        # Add some text for OCR detection (coordinates)
        cv2.putText(game_image, "K1 (123,456)", (400, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Add resource counter text
        cv2.putText(game_image, "Gold: 10000/20000", (50, 350), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Mock the window service methods
        window_service.capture_screenshot = MagicMock(return_value=game_image)
        window_service.find_window = MagicMock(return_value=True)
        window_service.get_window_position = MagicMock(return_value=(0, 0, 600, 400))
        
        return window_service
    
    def _create_detection_service(self):
        """Create a detection service with test strategies."""
        # Create detection service
        detection_service = DetectionService(self.event_bus, self.window_service)
        
        # Register template strategy
        template_strategy = TemplateMatchingStrategy(templates_dir=self.templates_dir)
        detection_service.register_strategy('template', template_strategy)
        
        # Mock OCR strategy
        ocr_strategy = MagicMock(spec=OCRStrategy)
        
        # Configure OCR mock to return predefined results
        def mock_detect(image, **kwargs):
            # Convert image to text for testing
            height, width = image.shape[:2]
            
            # Find text that looks like coordinates
            if height > 100 and width > 350:
                return [
                    {
                        'text': 'K1 (123,456)',
                        'confidence': 0.9,
                        'x': 400, 'y': 30,
                        'width': 120, 'height': 30
                    }
                ]
            # Find text that looks like resource counts
            elif 300 <= height <= 400 and width >= 50:
                return [
                    {
                        'text': 'Gold: 10000/20000',
                        'confidence': 0.95,
                        'x': 50, 'y': 350,
                        'width': 150, 'height': 20
                    }
                ]
            else:
                return []
                
        ocr_strategy.detect = mock_detect
        ocr_strategy.get_name.return_value = 'OCR Strategy'
        detection_service.register_strategy('ocr', ocr_strategy)
        
        return detection_service
    
    def test_detect_and_update_coordinates(self):
        """Test that GameService can update coordinates from detection results."""
        # Call update method (this should trigger coordinate detection)
        self.game_service.update_current_position()
        
        # Verify game state was updated with the correct coordinates
        self.assertIsNotNone(self.game_service.state.current_position)
        self.assertEqual(self.game_service.state.current_position.kingdom, 1)
        self.assertEqual(self.game_service.state.current_position.x, 123)
        self.assertEqual(self.game_service.state.current_position.y, 456)
        
        # Verify events were published
        self.assertGreater(len(self.received_events), 0)
        
        # Find the coordinates update event
        coords_event = None
        for event in self.received_events:
            if 'coordinates' in event.data:
                coords_event = event
                break
                
        self.assertIsNotNone(coords_event)
        self.assertEqual(coords_event.data['coordinates'], 'K1 (123,456)')
    
    def test_detect_and_update_resources(self):
        """Test that GameService can update resources from detection results."""
        # Call update method (this should trigger resource detection)
        self.game_service.update_resources()
        
        # Verify game state was updated with the correct resources
        resources = self.game_service.state.resources
        self.assertIsNotNone(resources)
        
        # Check gold resource
        gold = resources.get('gold')
        self.assertIsNotNone(gold)
        self.assertEqual(gold.amount, 10000)
        self.assertEqual(gold.capacity, 20000)
        
        # Verify events were published
        self.assertGreater(len(self.received_events), 0)
        
        # Find the resource update event
        resource_event = None
        for event in self.received_events:
            if 'resources' in event.data:
                resource_event = event
                break
                
        self.assertIsNotNone(resource_event)
    
    def test_detect_buildings(self):
        """Test that GameService can detect buildings on the map."""
        # Call update method (this should trigger building detection)
        self.game_service.update_buildings()
        
        # Verify game state was updated with the detected building
        buildings = self.game_service.state.buildings
        self.assertIsNotNone(buildings)
        self.assertGreater(len(buildings), 0)
        
        # Find the castle building
        castle = None
        for building in buildings:
            if 'castle' in building.name.lower():
                castle = building
                break
                
        self.assertIsNotNone(castle)
        
        # Verify events were published
        self.assertGreater(len(self.received_events), 0)
    
    def test_save_and_load_state(self):
        """Test that GameService can save and load state."""
        # Update state with some test data
        self.game_service.state.current_position = Coordinates(1, 123, 456)
        self.game_service.update_resources()  # This will add resources
        
        # Save state
        self.game_service.save_state()
        
        # Create a new game service instance
        new_game_service = GameService(
            self.event_bus,
            self.detection_service,
            state_file_path=os.path.join(self.state_dir, 'game_state.json')
        )
        
        # Verify state was loaded correctly
        self.assertEqual(new_game_service.state.current_position.kingdom, 1)
        self.assertEqual(new_game_service.state.current_position.x, 123)
        self.assertEqual(new_game_service.state.current_position.y, 456)
        
        # Check resource
        gold = new_game_service.state.resources.get('gold')
        self.assertIsNotNone(gold)
        self.assertEqual(gold.amount, 10000)
    
    def test_game_service_event_propagation(self):
        """Test that events from detection service propagate to game service."""
        # Subscribe to detection events
        detection_events = []
        self.event_bus.subscribe(EventType.DETECTION_COMPLETED, 
                                lambda e: detection_events.append(e))
        
        # Trigger detection through game service
        self.game_service.update_current_position()
        
        # Verify both detection and game state events were published
        self.assertGreater(len(detection_events), 0)
        self.assertGreater(len(self.received_events), 0)
        
        # Check event causality - game state event should happen after detection event
        detection_time = detection_events[0].timestamp
        game_time = self.received_events[0].timestamp
        self.assertGreaterEqual(game_time, detection_time)


if __name__ == '__main__':
    unittest.main() 