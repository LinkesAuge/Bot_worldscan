"""
End-to-End Integration Tests

These tests verify complete workflows from end to end,
ensuring all Scout components work together properly in real-world scenarios.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import tempfile
from pathlib import Path
import json
import time
import cv2
import numpy as np

# Add parent directory to path to allow running as standalone
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Import core services
from scout.core.window.window_service import WindowService
from scout.core.detection.detection_service import DetectionService
from scout.core.detection.strategies.template_strategy import TemplateStrategy
from scout.core.game.game_service import GameService
from scout.core.game.game_state import GameState
from scout.core.automation.automation_service import AutomationService
from scout.core.automation.task import Task, TaskStatus
from scout.core.events.event_bus import EventBus
from scout.core.events.event_types import EventType
from scout.core.services.service_locator import ServiceLocator
from scout.core.error_reporting.error_handler import ErrorHandler


class TestEndToEndIntegration(unittest.TestCase):
    """Test complete end-to-end workflows involving multiple components."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create event bus for communication
        self.event_bus = EventBus()
        
        # Create service locator
        self.service_locator = MagicMock(spec=ServiceLocator)
        self.service_locator.get_event_bus.return_value = self.event_bus
        
        # Create error handler
        self.error_handler = ErrorHandler(self.service_locator)
        self.service_locator.get_error_handler.return_value = self.error_handler
        
        # Create core services
        self.window_service = WindowService(self.service_locator)
        self.detection_service = DetectionService(self.service_locator)
        self.game_service = GameService(self.service_locator)
        self.automation_service = AutomationService(self.service_locator)
        
        # Register template strategy
        self.detection_service.register_strategy("template", TemplateStrategy())
        
        # Register services with service locator
        self.service_locator.get_window_service.return_value = self.window_service
        self.service_locator.get_detection_service.return_value = self.detection_service
        self.service_locator.get_game_service.return_value = self.game_service
        self.service_locator.get_automation_service.return_value = self.automation_service
        
        # Create temporary directory for test data
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create test images and data
        self.create_test_data()
        
        # Track events
        self.received_events = []
        self.event_bus.subscribe(EventType.WINDOW_SELECTED, self._on_event)
        self.event_bus.subscribe(EventType.DETECTION_REQUESTED, self._on_event)
        self.event_bus.subscribe(EventType.DETECTION_COMPLETED, self._on_event)
        self.event_bus.subscribe(EventType.GAME_STATE_UPDATED, self._on_event)
        self.event_bus.subscribe(EventType.AUTOMATION_STARTED, self._on_event)
        self.event_bus.subscribe(EventType.AUTOMATION_COMPLETED, self._on_event)
        self.event_bus.subscribe(EventType.ERROR_OCCURRED, self._on_event)

    def tearDown(self):
        """Clean up after each test."""
        self.temp_dir.cleanup()
        
    def _on_event(self, event):
        """Store received events for verification."""
        self.received_events.append(event)

    def create_test_data(self):
        """Create test images and data for end-to-end testing."""
        # Create resource images
        
        # Create game screen
        self.game_screen = np.zeros((800, 1200, 3), dtype=np.uint8)
        
        # Add resource indicators
        # Gold resource
        cv2.rectangle(self.game_screen, (50, 50), (100, 70), (0, 215, 255), -1)  # Gold color (BGR)
        cv2.putText(self.game_screen, "1000", (110, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Wood resource
        cv2.rectangle(self.game_screen, (200, 50), (250, 70), (42, 42, 165), -1)  # Brown color (BGR)
        cv2.putText(self.game_screen, "500", (260, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Stone resource
        cv2.rectangle(self.game_screen, (350, 50), (400, 70), (128, 128, 128), -1)  # Gray color (BGR)
        cv2.putText(self.game_screen, "200", (410, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add buildings
        # Town hall
        cv2.rectangle(self.game_screen, (300, 300), (400, 350), (100, 100, 100), -1)
        cv2.putText(self.game_screen, "Town Hall", (320, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Barracks
        cv2.rectangle(self.game_screen, (500, 300), (600, 350), (50, 50, 150), -1)
        cv2.putText(self.game_screen, "Barracks", (520, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Farm
        cv2.rectangle(self.game_screen, (700, 300), (800, 350), (50, 150, 50), -1)
        cv2.putText(self.game_screen, "Farm", (730, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add resource node
        cv2.circle(self.game_screen, (900, 500), 30, (0, 215, 255), -1)  # Gold node
        
        # Save game screen
        self.game_screen_path = self.temp_path / "game_screen.png"
        cv2.imwrite(str(self.game_screen_path), self.game_screen)
        
        # Create templates for resources and buildings
        # Gold template
        self.gold_template = self.game_screen[45:75, 45:105].copy()
        self.gold_template_path = self.temp_path / "gold_template.png"
        cv2.imwrite(str(self.gold_template_path), self.gold_template)
        
        # Wood template
        self.wood_template = self.game_screen[45:75, 195:255].copy()
        self.wood_template_path = self.temp_path / "wood_template.png"
        cv2.imwrite(str(self.wood_template_path), self.wood_template)
        
        # Stone template
        self.stone_template = self.game_screen[45:75, 345:405].copy()
        self.stone_template_path = self.temp_path / "stone_template.png"
        cv2.imwrite(str(self.stone_template_path), self.stone_template)
        
        # Town hall template
        self.townhall_template = self.game_screen[295:355, 295:405].copy()
        self.townhall_template_path = self.temp_path / "townhall_template.png"
        cv2.imwrite(str(self.townhall_template_path), self.townhall_template)
        
        # Barracks template
        self.barracks_template = self.game_screen[295:355, 495:605].copy()
        self.barracks_template_path = self.temp_path / "barracks_template.png"
        cv2.imwrite(str(self.barracks_template_path), self.barracks_template)
        
        # Farm template
        self.farm_template = self.game_screen[295:355, 695:805].copy()
        self.farm_template_path = self.temp_path / "farm_template.png"
        cv2.imwrite(str(self.farm_template_path), self.farm_template)
        
        # Gold node template
        self.gold_node_template = self.game_screen[470:530, 870:930].copy()
        self.gold_node_template_path = self.temp_path / "gold_node_template.png"
        cv2.imwrite(str(self.gold_node_template_path), self.gold_node_template)
        
        # Create resource configuration
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
                },
                {
                    "name": "stone",
                    "template": str(self.stone_template_path),
                    "value_offset": {"x": 60, "y": 15},
                    "value_width": 50,
                    "ocr_config": "--psm 7 -c tessedit_char_whitelist=0123456789"
                }
            ]
        }
        
        # Create building configuration
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
                },
                {
                    "name": "farm",
                    "template": str(self.farm_template_path),
                    "type": "food",
                    "level": 1
                }
            ]
        }
        
        # Create map element configuration
        self.map_element_config = {
            "map_elements": [
                {
                    "name": "gold_node",
                    "template": str(self.gold_node_template_path),
                    "type": "resource",
                    "resource_type": "gold"
                }
            ]
        }
        
        # Save configurations
        self.resource_config_path = self.temp_path / "resource_config.json"
        with open(self.resource_config_path, 'w') as f:
            json.dump(self.resource_config, f)
            
        self.building_config_path = self.temp_path / "building_config.json"
        with open(self.building_config_path, 'w') as f:
            json.dump(self.building_config, f)
            
        self.map_element_config_path = self.temp_path / "map_element_config.json"
        with open(self.map_element_config_path, 'w') as f:
            json.dump(self.map_element_config, f)

    def create_mock_task(self, name, action_type, duration=0.1, success=True, update_func=None):
        """Create a mock task for testing."""
        task = Task(name, action_type)
        
        # Add mock execute method
        def mock_execute(context=None):
            # Simulate task execution time
            time.sleep(duration)
            
            # Call update function if provided
            if update_func and callable(update_func):
                update_func(context)
                
            # Return result
            result = Task.Result()
            result.success = success
            result.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            result.message = f"{name} {'completed successfully' if success else 'failed'}"
            return result
            
        task.execute = mock_execute
        return task
    
    def test_resource_collection_workflow(self):
        """
        Test E2E-001: Resource collection workflow.
        
        Tests the full resource collection workflow from window selection
        to detection to game state update to automation.
        """
        # Set up mock window capture
        self.window_service.select_window = MagicMock(return_value=True)
        self.window_service.capture_window = MagicMock(return_value=str(self.game_screen_path))
        
        # Mock OCR detection for resource values
        with patch('scout.core.detection.strategies.ocr_strategy.OCRStrategy.detect') as mock_ocr:
            # Configure mock OCR to return resource values
            mock_ocr.side_effect = [
                {"text": "1000", "confidence": 0.9},  # Gold value
                {"text": "500", "confidence": 0.9},   # Wood value
                {"text": "200", "confidence": 0.9}    # Stone value
            ]
            
            # Configure game service for resources
            with open(self.resource_config_path, 'r') as f:
                resource_config = json.load(f)
            self.game_service.configure_resources(resource_config["resources"])
            
            # Step 1: Select window
            self.window_service.select_window("Game Window")
            
            # Step 2: Detect resources
            detection_results = []
            for resource in resource_config["resources"]:
                # Detect each resource template
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
            
            # Step 3: Update game state with detected resources
            self.game_service.update_resources(detection_results, str(self.game_screen_path))
            
            # Step 4: Verify game state contains resources
            game_state = self.game_service.get_game_state()
            self.assertIn("resources", game_state)
            self.assertEqual(len(game_state["resources"]), 3)
            
            # Check specific resources
            resources = {r["name"]: r["value"] for r in game_state["resources"]}
            self.assertEqual(resources["gold"], 1000)
            self.assertEqual(resources["wood"], 500)
            self.assertEqual(resources["stone"], 200)
            
            # Step 5: Create an automation task that collects resources
            def collect_gold(context):
                # Update game state with new gold amount
                current_state = self.game_service.get_game_state()
                new_state = GameState.from_dict(current_state)
                
                # Update gold amount (collect 100 gold)
                for resource in new_state.get_resources():
                    if resource["name"] == "gold":
                        resource["value"] += 100
                
                # Set new state
                self.game_service.set_game_state(new_state)
                
            collect_task = self.create_mock_task(
                "Collect Gold", 
                "collect", 
                duration=0.1, 
                success=True,
                update_func=collect_gold
            )
            
            # Step 6: Execute automation task
            self.automation_service.execute_task(collect_task, context=game_state)
            
            # Step 7: Verify resource amount was updated
            updated_state = self.game_service.get_game_state()
            updated_resources = {r["name"]: r["value"] for r in updated_state["resources"]}
            self.assertEqual(updated_resources["gold"], 1100)  # 1000 + 100
            
            # Step 8: Verify events were published in the correct sequence
            event_types = [e.type for e in self.received_events]
            
            # Check event sequence
            self.assertIn(EventType.WINDOW_SELECTED, event_types)
            self.assertIn(EventType.DETECTION_COMPLETED, event_types)
            self.assertIn(EventType.GAME_STATE_UPDATED, event_types)
            self.assertIn(EventType.AUTOMATION_STARTED, event_types)
            
            # Check order of key events
            window_selected_idx = event_types.index(EventType.WINDOW_SELECTED)
            detection_completed_idx = event_types.index(EventType.DETECTION_COMPLETED)
            game_state_updated_idx = event_types.index(EventType.GAME_STATE_UPDATED)
            
            self.assertLess(window_selected_idx, detection_completed_idx)
            self.assertLess(detection_completed_idx, game_state_updated_idx)

    def test_building_upgrade_workflow(self):
        """
        Test E2E-002: Building upgrade workflow.
        
        Tests the full building upgrade workflow from building detection
        to game state update to upgrade automation.
        """
        # Set up mock window capture
        self.window_service.select_window = MagicMock(return_value=True)
        self.window_service.capture_window = MagicMock(return_value=str(self.game_screen_path))
        
        # Step 1: Configure game service for buildings
        with open(self.building_config_path, 'r') as f:
            building_config = json.load(f)
        self.game_service.configure_buildings(building_config["buildings"])
        
        # Step 2: Detect buildings
        detection_results = []
        for building in building_config["buildings"]:
            # Detect each building template
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
        
        # Step 3: Update game state with detected buildings
        self.game_service.update_buildings(detection_results, str(self.game_screen_path))
        
        # Step 4: Verify game state contains buildings
        game_state = self.game_service.get_game_state()
        self.assertIn("buildings", game_state)
        self.assertEqual(len(game_state["buildings"]), 3)
        
        # Check specific buildings
        buildings = {b["name"]: b for b in game_state["buildings"]}
        self.assertIn("townhall", buildings)
        self.assertIn("barracks", buildings)
        self.assertIn("farm", buildings)
        
        # Step 5: Create a task to upgrade a building
        def upgrade_townhall(context):
            # Update game state with upgraded townhall
            current_state = self.game_service.get_game_state()
            new_state = GameState.from_dict(current_state)
            
            # Find and upgrade townhall
            for building in new_state.get_buildings():
                if building["name"] == "townhall":
                    building["level"] = 2
            
            # Deduct resources used for upgrade
            for resource in new_state.get_resources():
                if resource["name"] == "gold":
                    resource["value"] -= 500
                if resource["name"] == "wood":
                    resource["value"] -= 300
            
            # Set new state
            self.game_service.set_game_state(new_state)
        
        # First add initial resources
        initial_state = GameState.from_dict(game_state)
        initial_state.add_resource("gold", 1000)
        initial_state.add_resource("wood", 600)
        initial_state.add_resource("stone", 300)
        self.game_service.set_game_state(initial_state)
        
        # Create upgrade task
        upgrade_task = self.create_mock_task(
            "Upgrade Town Hall", 
            "upgrade", 
            duration=0.2, 
            success=True,
            update_func=upgrade_townhall
        )
        
        # Step 6: Execute upgrade task
        self.automation_service.execute_task(upgrade_task, context=game_state)
        
        # Step 7: Verify building was upgraded
        updated_state = self.game_service.get_game_state()
        updated_buildings = {b["name"]: b for b in updated_state["buildings"]}
        self.assertEqual(updated_buildings["townhall"]["level"], 2)
        
        # Verify resources were deducted
        updated_resources = {r["name"]: r["value"] for r in updated_state["resources"]}
        self.assertEqual(updated_resources["gold"], 500)  # 1000 - 500
        self.assertEqual(updated_resources["wood"], 300)  # 600 - 300
        
        # Step 8: Verify events were published
        event_types = [e.type for e in self.received_events]
        self.assertIn(EventType.GAME_STATE_UPDATED, event_types)
        self.assertIn(EventType.AUTOMATION_STARTED, event_types)

    def test_error_recovery_during_workflow(self):
        """
        Test E2E-003: Error recovery during workflow.
        
        Tests that the system can recover from errors during a workflow.
        """
        # Set up mock window capture
        self.window_service.select_window = MagicMock(return_value=True)
        self.window_service.capture_window = MagicMock(return_value=str(self.game_screen_path))
        
        # Configure initial game state
        initial_state = GameState()
        initial_state.add_resource("gold", 1000)
        initial_state.add_resource("wood", 500)
        self.game_service.set_game_state(initial_state)
        
        # Create a sequence of tasks, with one that fails
        def update_gold(context):
            current_state = self.game_service.get_game_state()
            new_state = GameState.from_dict(current_state)
            
            for resource in new_state.get_resources():
                if resource["name"] == "gold":
                    resource["value"] += 100
            
            self.game_service.set_game_state(new_state)
        
        def failing_task_function(context):
            # This task will fail but the error handler should recover
            raise ValueError("Simulated error in task")
        
        def update_wood(context):
            current_state = self.game_service.get_game_state()
            new_state = GameState.from_dict(current_state)
            
            for resource in new_state.get_resources():
                if resource["name"] == "wood":
                    resource["value"] += 100
            
            self.game_service.set_game_state(new_state)
        
        # Create task sequence
        gold_task = self.create_mock_task(
            "Collect Gold", 
            "collect", 
            update_func=update_gold
        )
        
        failing_task = self.create_mock_task(
            "Failing Task",
            "fail"
        )
        
        # Modify execute method to actually fail
        failing_task.execute = failing_task_function
        
        wood_task = self.create_mock_task(
            "Collect Wood", 
            "collect", 
            update_func=update_wood
        )
        
        task_sequence = [gold_task, failing_task, wood_task]
        
        # Set up error handling
        # Mock recovery strategy
        def mock_recover_from_error(error, context):
            # Log error but continue
            self.event_bus.publish(EventType.ERROR_OCCURRED, {
                "message": str(error),
                "recovery": "continuing with next task"
            })
            return True
        
        # Register recovery strategy with error handler
        self.error_handler.register_recovery_strategy(ValueError, mock_recover_from_error)
        
        # Execute the sequence with error recovery
        self.automation_service.execute_sequence(task_sequence, continue_on_error=True)
        
        # Wait for tasks to complete
        time.sleep(0.5)
        
        # Verify state after execution
        final_state = self.game_service.get_game_state()
        resources = {r["name"]: r["value"] for r in final_state["resources"]}
        
        # Gold task should have executed
        self.assertEqual(resources["gold"], 1100)  # 1000 + 100
        
        # Wood task should have executed despite the failing task
        self.assertEqual(resources["wood"], 600)  # 500 + 100
        
        # Verify events
        event_types = [e.type for e in self.received_events]
        
        # Should have error event
        self.assertIn(EventType.ERROR_OCCURRED, event_types)
        
        # Should still have completed event for successful tasks
        automation_completed_events = [e for e in self.received_events if e.type == EventType.AUTOMATION_COMPLETED]
        self.assertGreaterEqual(len(automation_completed_events), 2)  # At least 2 tasks completed


if __name__ == "__main__":
    unittest.main() 