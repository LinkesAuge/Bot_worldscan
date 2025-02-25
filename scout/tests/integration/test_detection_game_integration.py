"""
Detection-Game Integration Tests

These tests verify that the Detection Service and Game Service
components integrate correctly and work together properly.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import tempfile
from pathlib import Path
import json
import cv2
import numpy as np

# Add parent directory to path to allow running as standalone
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from scout.core.detection.detection_service import DetectionService
from scout.core.detection.strategies.template_strategy import TemplateStrategy
from scout.core.game.game_service import GameService
from scout.core.game.game_state import GameState
from scout.core.events.event_bus import EventBus
from scout.core.events.event_types import EventType
from scout.core.services.service_locator import ServiceLocator


class TestDetectionGameIntegration(unittest.TestCase):
    """Test the integration between DetectionService and GameService."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create event bus for communication
        self.event_bus = EventBus()
        
        # Create mock service locator
        self.service_locator = MagicMock(spec=ServiceLocator)
        self.service_locator.get_event_bus.return_value = self.event_bus
        
        # Create detection service with template strategy
        self.detection_service = DetectionService(self.service_locator)
        self.detection_service.register_strategy("template", TemplateStrategy())
        
        # Create game service
        self.game_service = GameService(self.service_locator)
        
        # Mock service locator to return our services
        self.service_locator.get_detection_service.return_value = self.detection_service
        self.service_locator.get_game_service.return_value = self.game_service
        
        # Create temporary directory for test images
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create test images for resources and buildings
        self.create_test_images()
        
        # Configure event listeners
        self.received_events = []
        self.event_bus.subscribe(EventType.GAME_STATE_UPDATED, self._on_event)
        self.event_bus.subscribe(EventType.DETECTION_COMPLETED, self._on_event)

    def tearDown(self):
        """Clean up after each test."""
        self.temp_dir.cleanup()
    
    def _on_event(self, event):
        """Store received events for verification."""
        self.received_events.append(event)

    def create_test_images(self):
        """Create test images for resources and buildings."""
        # Create a base game screen
        self.game_screen = np.zeros((600, 800, 3), dtype=np.uint8)
        
        # Add resource icons
        # Gold resource
        cv2.rectangle(self.game_screen, (50, 50), (100, 70), (0, 215, 255), -1)  # Gold color (BGR)
        cv2.putText(self.game_screen, "1000", (110, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Wood resource
        cv2.rectangle(self.game_screen, (50, 90), (100, 110), (42, 42, 165), -1)  # Brown color (BGR)
        cv2.putText(self.game_screen, "500", (110, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add building icons
        # Town hall
        cv2.rectangle(self.game_screen, (300, 300), (400, 350), (100, 100, 100), -1)
        cv2.putText(self.game_screen, "Town Hall", (320, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Barracks
        cv2.rectangle(self.game_screen, (450, 300), (550, 350), (50, 50, 150), -1)
        cv2.putText(self.game_screen, "Barracks", (470, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Save the game screen
        self.game_screen_path = self.temp_path / "game_screen.png"
        cv2.imwrite(str(self.game_screen_path), self.game_screen)
        
        # Create templates for resources
        # Gold template
        self.gold_template = self.game_screen[45:75, 45:105].copy()
        self.gold_template_path = self.temp_path / "gold_template.png"
        cv2.imwrite(str(self.gold_template_path), self.gold_template)
        
        # Wood template
        self.wood_template = self.game_screen[85:115, 45:105].copy()
        self.wood_template_path = self.temp_path / "wood_template.png"
        cv2.imwrite(str(self.wood_template_path), self.wood_template)
        
        # Create templates for buildings
        # Town hall template
        self.townhall_template = self.game_screen[295:355, 295:405].copy()
        self.townhall_template_path = self.temp_path / "townhall_template.png"
        cv2.imwrite(str(self.townhall_template_path), self.townhall_template)
        
        # Barracks template
        self.barracks_template = self.game_screen[295:355, 445:555].copy()
        self.barracks_template_path = self.temp_path / "barracks_template.png"
        cv2.imwrite(str(self.barracks_template_path), self.barracks_template)
        
        # Create resource configuration file
        self.resource_config = {
            "resources": [
                {
                    "name": "gold",
                    "template": str(self.gold_template_path),
                    "value_offset": {"x": 60, "y": 15},
                    "value_width": 50,
                    "ocr_config": "--psm 7 -c tessedit_char_whitelist=0123456789"
                },
                {
                    "name": "wood",
                    "template": str(self.wood_template_path),
                    "value_offset": {"x": 60, "y": 15},
                    "value_width": 50,
                    "ocr_config": "--psm 7 -c tessedit_char_whitelist=0123456789"
                }
            ]
        }
        
        self.resource_config_path = self.temp_path / "resource_config.json"
        with open(self.resource_config_path, 'w') as f:
            json.dump(self.resource_config, f)
        
        # Create building configuration file
        self.building_config = {
            "buildings": [
                {
                    "name": "townhall",
                    "template": str(self.townhall_template_path),
                    "type": "production",
                    "level": 1
                },
                {
                    "name": "barracks",
                    "template": str(self.barracks_template_path),
                    "type": "military",
                    "level": 1
                }
            ]
        }
        
        self.building_config_path = self.temp_path / "building_config.json"
        with open(self.building_config_path, 'w') as f:
            json.dump(self.building_config, f)

    def test_resource_detection_to_game_state(self):
        """
        Test DG-INT-001: Resource detection to game state.
        
        Verify that detected resources appear in the game state.
        """
        # Mock OCR detection for resource values
        with patch('scout.core.detection.strategies.ocr_strategy.OCRStrategy.detect') as mock_ocr:
            # Configure mock OCR to return resource values
            mock_ocr.side_effect = [
                {"text": "1000", "confidence": 0.9},  # Gold value
                {"text": "500", "confidence": 0.9}    # Wood value
            ]
            
            # Load resource configuration
            with open(self.resource_config_path, 'r') as f:
                resource_config = json.load(f)
            
            # Configure game service to use these resources
            self.game_service.configure_resources(resource_config["resources"])
            
            # Run resource detection
            detection_results = []
            for resource in resource_config["resources"]:
                # Detect the resource template
                template_config = {
                    "templates": [resource["template"]],
                    "threshold": 0.7,
                    "limit": 1,
                    "visualize": False
                }
                
                result = self.detection_service.detect(
                    str(self.game_screen_path),
                    strategy="template",
                    config=template_config
                )
                
                if "matches" in result and len(result["matches"]) > 0:
                    match = result["matches"][0]
                    detection_results.append({
                        "resource": resource["name"],
                        "match": match,
                        "template": resource["template"],
                        "value_offset": resource["value_offset"],
                        "value_width": resource["value_width"]
                    })
            
            # Update game state with detection results
            self.game_service.update_resources(detection_results, str(self.game_screen_path))
            
            # Verify game state has been updated
            game_state = self.game_service.get_game_state()
            
            # Check resources in game state
            self.assertIn("resources", game_state)
            self.assertEqual(len(game_state["resources"]), 2)
            
            # Check specific resource values
            resources = {r["name"]: r["value"] for r in game_state["resources"]}
            self.assertIn("gold", resources)
            self.assertIn("wood", resources)
            self.assertEqual(resources["gold"], 1000)
            self.assertEqual(resources["wood"], 500)
            
            # Verify events were published
            self.assertGreaterEqual(len(self.received_events), 1)
            event_types = [e.type for e in self.received_events]
            self.assertIn(EventType.GAME_STATE_UPDATED, event_types)

    def test_building_detection_to_game_state(self):
        """
        Test DG-INT-002: Building detection to game state.
        
        Verify that detected buildings appear in the game state.
        """
        # Load building configuration
        with open(self.building_config_path, 'r') as f:
            building_config = json.load(f)
        
        # Configure game service to use these buildings
        self.game_service.configure_buildings(building_config["buildings"])
        
        # Run building detection
        detection_results = []
        for building in building_config["buildings"]:
            # Detect the building template
            template_config = {
                "templates": [building["template"]],
                "threshold": 0.7,
                "limit": 1,
                "visualize": False
            }
            
            result = self.detection_service.detect(
                str(self.game_screen_path),
                strategy="template",
                config=template_config
            )
            
            if "matches" in result and len(result["matches"]) > 0:
                match = result["matches"][0]
                detection_results.append({
                    "building": building["name"],
                    "match": match,
                    "type": building["type"],
                    "level": building["level"],
                    "template": building["template"]
                })
        
        # Update game state with detection results
        self.game_service.update_buildings(detection_results, str(self.game_screen_path))
        
        # Verify game state has been updated
        game_state = self.game_service.get_game_state()
        
        # Check buildings in game state
        self.assertIn("buildings", game_state)
        self.assertEqual(len(game_state["buildings"]), 2)
        
        # Check specific buildings
        buildings = {b["name"]: b for b in game_state["buildings"]}
        self.assertIn("townhall", buildings)
        self.assertIn("barracks", buildings)
        self.assertEqual(buildings["townhall"]["type"], "production")
        self.assertEqual(buildings["barracks"]["type"], "military")
        
        # Verify events were published
        self.assertGreaterEqual(len(self.received_events), 1)
        event_types = [e.type for e in self.received_events]
        self.assertIn(EventType.GAME_STATE_UPDATED, event_types)

    def test_map_element_detection(self):
        """
        Test DG-INT-003: Map element detection.
        
        Verify that detected map elements appear in the game map view.
        """
        # Create a simple map with some elements
        map_image = np.zeros((400, 400, 3), dtype=np.uint8)
        
        # Add some map elements
        # Resource node
        cv2.circle(map_image, (100, 100), 20, (0, 215, 255), -1)  # Gold resource
        
        # Enemy base
        cv2.rectangle(map_image, (250, 250), (300, 300), (0, 0, 255), -1)  # Red for enemy
        
        # Friendly outpost
        cv2.rectangle(map_image, (300, 100), (350, 150), (0, 255, 0), -1)  # Green for friendly
        
        # Save the map image
        map_image_path = self.temp_path / "map_image.png"
        cv2.imwrite(str(map_image_path), map_image)
        
        # Create templates for map elements
        # Resource node template
        resource_node_template = map_image[80:120, 80:120].copy()
        resource_node_template_path = self.temp_path / "resource_node_template.png"
        cv2.imwrite(str(resource_node_template_path), resource_node_template)
        
        # Enemy base template
        enemy_base_template = map_image[245:305, 245:305].copy()
        enemy_base_template_path = self.temp_path / "enemy_base_template.png"
        cv2.imwrite(str(enemy_base_template_path), enemy_base_template)
        
        # Friendly outpost template
        friendly_outpost_template = map_image[95:155, 295:355].copy()
        friendly_outpost_template_path = self.temp_path / "friendly_outpost_template.png"
        cv2.imwrite(str(friendly_outpost_template_path), friendly_outpost_template)
        
        # Define map elements configuration
        map_elements_config = [
            {
                "name": "resource_node",
                "template": str(resource_node_template_path),
                "type": "resource",
                "resource_type": "gold"
            },
            {
                "name": "enemy_base",
                "template": str(enemy_base_template_path),
                "type": "enemy",
                "threat_level": "high"
            },
            {
                "name": "friendly_outpost",
                "template": str(friendly_outpost_template_path),
                "type": "friendly",
                "unit_capacity": 10
            }
        ]
        
        # Configure game service for map elements
        self.game_service.configure_map_elements(map_elements_config)
        
        # Run map element detection
        detection_results = []
        for element in map_elements_config:
            # Detect the map element template
            template_config = {
                "templates": [element["template"]],
                "threshold": 0.7,
                "limit": 1,
                "visualize": False
            }
            
            result = self.detection_service.detect(
                str(map_image_path),
                strategy="template",
                config=template_config
            )
            
            if "matches" in result and len(result["matches"]) > 0:
                match = result["matches"][0]
                detection_results.append({
                    "element": element["name"],
                    "match": match,
                    "type": element["type"],
                    "template": element["template"],
                    "properties": {k: v for k, v in element.items() 
                                  if k not in ["name", "template", "type"]}
                })
        
        # Update game state with map element detection results
        self.game_service.update_map_elements(detection_results, str(map_image_path))
        
        # Verify game state has been updated
        game_state = self.game_service.get_game_state()
        
        # Check map elements in game state
        self.assertIn("map_elements", game_state)
        self.assertEqual(len(game_state["map_elements"]), 3)
        
        # Check specific map elements
        element_types = [e["type"] for e in game_state["map_elements"]]
        self.assertIn("resource", element_types)
        self.assertIn("enemy", element_types)
        self.assertIn("friendly", element_types)
        
        # Verify properties were preserved
        for element in game_state["map_elements"]:
            if element["type"] == "resource":
                self.assertEqual(element["properties"]["resource_type"], "gold")
            elif element["type"] == "enemy":
                self.assertEqual(element["properties"]["threat_level"], "high")
            elif element["type"] == "friendly":
                self.assertEqual(element["properties"]["unit_capacity"], 10)
        
        # Verify events were published
        self.assertGreaterEqual(len(self.received_events), 1)
        event_types = [e.type for e in self.received_events]
        self.assertIn(EventType.GAME_STATE_UPDATED, event_types)

    def test_game_state_influences_detection_parameters(self):
        """
        Test that game state can influence detection parameters.
        
        Verify that the game state can be used to adjust detection parameters.
        """
        # Initialize game state with specific values
        initial_state = GameState()
        initial_state.add_resource("gold", 1000)
        initial_state.add_resource("wood", 500)
        initial_state.add_building("townhall", {"type": "production", "level": 2})
        
        # Set initial game state
        self.game_service.set_game_state(initial_state)
        
        # Define detection parameters based on game state
        def get_detection_params(game_state):
            # Example: Adjust detection threshold based on townhall level
            townhall = next((b for b in game_state.get_buildings() if b["name"] == "townhall"), None)
            
            if townhall and townhall["level"] >= 2:
                # Higher level townhall enables more precise detection
                return {"threshold": 0.9, "multi_scale": True}
            else:
                # Lower level uses more lenient settings
                return {"threshold": 0.7, "multi_scale": False}
        
        # Get detection parameters based on current game state
        current_state = self.game_service.get_game_state()
        detection_params = get_detection_params(current_state)
        
        # Verify parameters are as expected for our initial state
        self.assertEqual(detection_params["threshold"], 0.9)
        self.assertTrue(detection_params["multi_scale"])
        
        # Run detection with these parameters
        template_config = {
            "templates": [str(self.gold_template_path)],
            "threshold": detection_params["threshold"],
            "multi_scale": detection_params["multi_scale"],
            "limit": 1,
            "visualize": False
        }
        
        result = self.detection_service.detect(
            str(self.game_screen_path),
            strategy="template",
            config=template_config
        )
        
        # Verify detection with these parameters works
        self.assertIsNotNone(result)
        self.assertIn("matches", result)
        
        # Now change game state and verify parameters change
        new_state = GameState()
        new_state.add_resource("gold", 1000)
        new_state.add_resource("wood", 500)
        new_state.add_building("townhall", {"type": "production", "level": 1})  # Lower level
        
        # Update game state
        self.game_service.set_game_state(new_state)
        
        # Get new detection parameters
        updated_state = self.game_service.get_game_state()
        updated_params = get_detection_params(updated_state)
        
        # Verify parameters changed
        self.assertEqual(updated_params["threshold"], 0.7)
        self.assertFalse(updated_params["multi_scale"])


if __name__ == "__main__":
    unittest.main() 