"""
Tests for the Game Service.

This module contains unit tests for the GameService class, which is responsible for
managing the game state through detection and window services.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from scout.core.window.window_service_interface import WindowServiceInterface
from scout.core.detection.detection_service_interface import DetectionServiceInterface
from scout.core.events.event_bus import EventBus
from scout.core.events.event_types import EventType
from scout.core.game.game_service import GameService
from scout.core.game.game_state import (
    GameState, Coordinates, Resource, Resources, Building, Army, MapEntity
)


class TestGameService(unittest.TestCase):
    """
    Test cases for the GameService class.
    
    This test suite verifies that:
    - The service can initialize properly
    - The service can detect game coordinates and resources
    - The service can save and load game state
    - The service processes detection events correctly
    - The service properly publishes events when state changes
    """
    
    def setUp(self):
        """Set up the test environment before each test method."""
        # Create mock dependencies
        self.window_service = MagicMock(spec=WindowServiceInterface)
        self.detection_service = MagicMock(spec=DetectionServiceInterface)
        self.event_bus = MagicMock(spec=EventBus)
        
        # Create a temporary file for state storage
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file_path = os.path.join(self.temp_dir.name, "game_state.json")
        
        # Create the service
        self.game_service = GameService(
            window_service=self.window_service,
            detection_service=self.detection_service,
            event_bus=self.event_bus,
            state_file_path=self.state_file_path
        )
    
    def tearDown(self):
        """Clean up the test environment after each test method."""
        # Remove the temporary directory
        self.temp_dir.cleanup()
    
    def test_initialization(self):
        """Test that the game service initializes correctly."""
        # Assert that the service's state is initialized
        self.assertIsNotNone(self.game_service.state)
        self.assertIsInstance(self.game_service.state, GameState)
        
        # Verify event subscription
        self.event_bus.subscribe.assert_called_once_with(
            EventType.DETECTION_COMPLETED,
            self.game_service._on_detection_completed
        )
    
    def test_update_coordinates(self):
        """Test that the service can update the player's coordinates."""
        # Setup mock for detection_service.get_text
        self.detection_service.get_text.return_value = "K:1 X:123 Y:456"
        
        # Call the method
        self.game_service._update_coordinates()
        
        # Verify detection service was called with the right parameters
        self.detection_service.get_text.assert_called_once()
        
        # Verify state was updated
        self.assertIsNotNone(self.game_service.state.current_position)
        self.assertEqual(self.game_service.state.current_position.kingdom, 1)
        self.assertEqual(self.game_service.state.current_position.x, 123)
        self.assertEqual(self.game_service.state.current_position.y, 456)
        
        # Verify coordinates were added to explored
        self.assertIn(self.game_service.state.current_position, 
                      self.game_service.state.explored_coordinates)
    
    def test_update_resources(self):
        """Test that the service can update resource information."""
        # Setup mock for detection_service.get_text
        self.detection_service.get_text.return_value = (
            "Gold: 1,234/5,000 Food: 2,345/10,000 "
            "Stone: 345/1,000 Wood: 456/2,000"
        )
        
        # Call the method
        self.game_service._update_resources()
        
        # Verify detection service was called
        self.detection_service.get_text.assert_called_once()
        
        # Verify state was updated
        resources = self.game_service.state.resources.as_dict()
        self.assertEqual(resources["gold"].amount, 1234)
        self.assertEqual(resources["gold"].capacity, 5000)
        self.assertEqual(resources["food"].amount, 2345)
        self.assertEqual(resources["food"].capacity, 10000)
    
    def test_save_and_load_state(self):
        """Test that the service can save and load state correctly."""
        # Populate state with test data
        self.game_service.state.player_name = "TestPlayer"
        self.game_service.state.player_level = 10
        self.game_service.state.current_position = Coordinates(1, 100, 200)
        self.game_service.state.resources.update("gold", 500, 1000)
        
        # Add a building
        building = Building("Barracks", 5)
        building.coordinates = Coordinates(1, 100, 201)
        self.game_service.state.buildings["Barracks"] = building
        
        # Save state
        self.game_service._save_state()
        
        # Create a new service with the same state file
        new_service = GameService(
            window_service=self.window_service,
            detection_service=self.detection_service,
            event_bus=self.event_bus,
            state_file_path=self.state_file_path
        )
        
        # Verify state was loaded correctly
        self.assertEqual(new_service.state.player_name, "TestPlayer")
        self.assertEqual(new_service.state.player_level, 10)
        self.assertEqual(new_service.state.current_position.kingdom, 1)
        self.assertEqual(new_service.state.current_position.x, 100)
        self.assertEqual(new_service.state.current_position.y, 200)
        
        # Verify resources were loaded
        self.assertEqual(
            new_service.state.resources.as_dict()["gold"].amount, 500)
        
        # Verify buildings were loaded
        self.assertIn("Barracks", new_service.state.buildings)
        self.assertEqual(new_service.state.buildings["Barracks"].level, 5)
    
    def test_process_template_results(self):
        """Test processing of template matching results."""
        # Create test detection results
        results = [
            {
                "template_name": "city_level5",
                "confidence": 0.95,
                "x": 100,
                "y": 200,
                "width": 50,
                "height": 50
            }
        ]
        
        # Setup state with current position
        self.game_service.state.current_position = Coordinates(1, 100, 200)
        
        # Mock _screen_to_game_coords to return a valid coordinate
        with patch.object(
            self.game_service,
            '_screen_to_game_coords',
            return_value=Coordinates(1, 101, 201)
        ):
            # Call the method
            self.game_service._process_template_results(results)
            
            # Verify entity was added to state
            coords = Coordinates(1, 101, 201)
            entity_key = f"{coords.kingdom}:{coords.x}:{coords.y}"
            self.assertIn(entity_key, self.game_service.state.known_entities)
            entity = self.game_service.state.known_entities[entity_key]
            self.assertEqual(entity.entity_type, "city")
            self.assertEqual(entity.coordinates, coords)
    
    def test_on_detection_completed(self):
        """Test handling of detection completed events."""
        # Create test event data
        event_data = {
            "strategy": "template",
            "results": [
                {
                    "template_name": "resource_node",
                    "confidence": 0.92,
                    "x": 150,
                    "y": 250,
                    "width": 30,
                    "height": 30
                }
            ]
        }
        
        # Mock _process_template_results
        with patch.object(self.game_service, '_process_template_results') as mock_process:
            # Call the method
            self.game_service._on_detection_completed(event_data)
            
            # Verify correct processing method was called
            mock_process.assert_called_once_with(event_data["results"])
    
    def test_update_state(self):
        """Test the main update_state method."""
        # Mock component methods
        with patch.object(self.game_service, '_update_coordinates') as mock_update_coords, \
             patch.object(self.game_service, '_update_resources') as mock_update_res, \
             patch.object(self.game_service, '_save_state') as mock_save, \
             patch.object(self.game_service, '_publish_state_changed_event') as mock_publish:
            
            # Call update_state
            self.game_service.update_state()
            
            # Verify all component methods were called
            mock_update_coords.assert_called_once()
            mock_update_res.assert_called_once()
            mock_save.assert_called_once()
            mock_publish.assert_called_once()
            
            # Verify last_updated was updated
            self.assertIsNotNone(self.game_service.state.last_updated)
    
    def test_configure_detection_regions(self):
        """Test that detection regions can be configured."""
        # Initial regions
        initial_regions = dict(self.game_service._regions)
        
        # New regions to add
        new_regions = {
            'buildings': {'left': 100, 'top': 200, 'width': 300, 'height': 400},
            'armies': {'left': 500, 'top': 600, 'width': 300, 'height': 200}
        }
        
        # Configure regions
        self.game_service.configure_detection_regions(new_regions)
        
        # Verify regions were added
        for key, region in new_regions.items():
            self.assertIn(key, self.game_service._regions)
            self.assertEqual(self.game_service._regions[key], region)
        
        # Verify existing regions were preserved
        for key, region in initial_regions.items():
            self.assertIn(key, self.game_service._regions)
            self.assertEqual(self.game_service._regions[key], region)
    
    def test_publish_state_changed_event(self):
        """Test that state changed events are published correctly."""
        # Setup state with test data
        self.game_service.state.current_position = Coordinates(1, 100, 200)
        self.game_service.state.resources.update("gold", 500, 1000)
        
        # Call the method
        self.game_service._publish_state_changed_event()
        
        # Verify event_bus.publish was called with correct event
        self.event_bus.publish.assert_called_once()
        
        # Get the event that was published
        call_args = self.event_bus.publish.call_args[0]
        event = call_args[0]
        
        # Verify event type
        self.assertEqual(event.event_type, EventType.GAME_STATE_CHANGED)
        
        # Verify event data
        self.assertEqual(event.data['current_position'], "K1 X100 Y200")
        self.assertEqual(event.data['resources']['gold'], 500)


if __name__ == '__main__':
    unittest.main() 