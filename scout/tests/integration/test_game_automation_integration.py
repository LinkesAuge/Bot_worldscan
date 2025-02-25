"""
Game-Automation Integration Tests

These tests verify that the Game Service and Automation Service
components integrate correctly and work together properly.
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

from scout.core.game.game_service import GameService
from scout.core.game.game_state import GameState
from scout.core.automation.automation_service import AutomationService
from scout.core.automation.task import Task, TaskStatus
from scout.core.events.event_bus import EventBus
from scout.core.events.event_types import EventType
from scout.core.services.service_locator import ServiceLocator


class TestGameAutomationIntegration(unittest.TestCase):
    """Test the integration between GameService and AutomationService."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create event bus for communication
        self.event_bus = EventBus()
        
        # Create mock service locator
        self.service_locator = MagicMock(spec=ServiceLocator)
        self.service_locator.get_event_bus.return_value = self.event_bus
        
        # Create game service
        self.game_service = GameService(self.service_locator)
        
        # Create automation service
        self.automation_service = AutomationService(self.service_locator)
        
        # Mock service locator to return our services
        self.service_locator.get_game_service.return_value = self.game_service
        self.service_locator.get_automation_service.return_value = self.automation_service
        
        # Create temporary directory for test data
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Set up initial game state
        self.setup_game_state()
        
        # Configure event listeners
        self.received_events = []
        self.event_bus.subscribe(EventType.GAME_STATE_UPDATED, self._on_event)
        self.event_bus.subscribe(EventType.TASK_STARTED, self._on_event)
        self.event_bus.subscribe(EventType.TASK_COMPLETED, self._on_event)
        self.event_bus.subscribe(EventType.TASK_FAILED, self._on_event)

    def tearDown(self):
        """Clean up after each test."""
        self.temp_dir.cleanup()
        
    def _on_event(self, event):
        """Store received events for verification."""
        self.received_events.append(event)

    def setup_game_state(self):
        """Set up initial game state for testing."""
        # Create initial game state
        initial_state = GameState()
        
        # Add resources
        initial_state.add_resource("gold", 1000)
        initial_state.add_resource("wood", 500)
        initial_state.add_resource("stone", 200)
        
        # Add buildings
        initial_state.add_building("townhall", {"type": "production", "level": 1, "position": {"x": 300, "y": 300}})
        initial_state.add_building("barracks", {"type": "military", "level": 1, "position": {"x": 450, "y": 300}})
        initial_state.add_building("mine", {"type": "resource", "level": 1, "position": {"x": 150, "y": 200}})
        
        # Add units
        initial_state.add_unit("worker", {"count": 5, "status": "idle"})
        initial_state.add_unit("soldier", {"count": 2, "status": "idle"})
        
        # Set current position
        initial_state.set_position("position", {"x": 500, "y": 500})
        
        # Set game state
        self.game_service.set_game_state(initial_state)

    def create_mock_task(self, name, action_type, duration=0.1, success=True):
        """Create a mock task for testing."""
        task = Task(name, action_type)
        
        # Add mock execute method
        original_execute = task.execute
        
        def mock_execute(context=None):
            if context is None:
                context = {}
            # Simulate task execution time
            time.sleep(duration)
            result = original_execute(context)
            result.success = success
            if success:
                result.status = TaskStatus.COMPLETED
            else:
                result.status = TaskStatus.FAILED
            return result
        
        task.execute = mock_execute
        return task

    def test_game_state_triggers_automation(self):
        """
        Test GA-INT-001: Game state triggers automation.
        
        Verify that automation sequence starts based on game state.
        """
        # Define a trigger condition based on game state
        def resource_trigger_condition(game_state):
            resources = {r["name"]: r["value"] for r in game_state["resources"]}
            return resources.get("gold", 0) >= 1000
        
        # Create a task sequence for the trigger
        task_sequence = [
            self.create_mock_task("Build Barracks", "build"),
            self.create_mock_task("Train Soldiers", "train")
        ]
        
        # Register trigger with automation service
        self.automation_service.register_trigger(
            "resource_trigger",
            resource_trigger_condition,
            task_sequence
        )
        
        # Manually check triggers (in real app this would be on a timer)
        self.automation_service.check_triggers(self.game_service.get_game_state())
        
        # Allow time for tasks to execute
        time.sleep(0.3)
        
        # Verify that tasks were executed
        self.assertGreaterEqual(len(self.received_events), 2)
        
        # Check specific events
        event_types = [e.type for e in self.received_events]
        self.assertIn(EventType.TASK_STARTED, event_types)
        self.assertIn(EventType.TASK_COMPLETED, event_types)
        
        # Get task names from events
        task_names = []
        for event in self.received_events:
            if event.type == EventType.TASK_STARTED and "task_name" in event.data:
                task_names.append(event.data["task_name"])
        
        # Verify both tasks were started
        self.assertIn("Build Barracks", task_names)
        self.assertIn("Train Soldiers", task_names)

    def test_automation_updates_game_state(self):
        """
        Test GA-INT-002: Automation updates game state.
        
        Verify that game state is updated after automation completes.
        """
        # Initial game state
        initial_state = self.game_service.get_game_state()
        
        # Create a task that will update game state
        build_task = Task("Build Farm", "build")
        
        # Mock the execute method to update game state
        def mock_execute(context=None):
            # Update game state with new building
            current_state = self.game_service.get_game_state()
            new_state = GameState.from_dict(current_state)
            new_state.add_building("farm", {"type": "food", "level": 1, "position": {"x": 400, "y": 400}})
            
            # Subtract resources used for building
            for resource in new_state.get_resources():
                if resource["name"] == "wood":
                    resource["value"] -= 100
                if resource["name"] == "stone":
                    resource["value"] -= 50
            
            # Update game state
            self.game_service.set_game_state(new_state)
            
            # Return success
            result = Task.Result()
            result.success = True
            result.status = TaskStatus.COMPLETED
            result.message = "Farm built successfully"
            return result
        
        build_task.execute = mock_execute
        
        # Execute the task
        self.automation_service.execute_task(build_task)
        
        # Verify game state was updated
        updated_state = self.game_service.get_game_state()
        
        # Check for new building
        buildings = {b["name"]: b for b in updated_state["buildings"]}
        self.assertIn("farm", buildings)
        
        # Check resources were deducted
        resources = {r["name"]: r["value"] for r in updated_state["resources"]}
        self.assertEqual(resources["wood"], 400)  # 500 - 100
        self.assertEqual(resources["stone"], 150)  # 200 - 50
        
        # Verify events were published
        self.assertGreaterEqual(len(self.received_events), 2)
        event_types = [e.type for e in self.received_events]
        self.assertIn(EventType.GAME_STATE_UPDATED, event_types)
        self.assertIn(EventType.TASK_COMPLETED, event_types)

    def test_conditional_automation_based_on_state(self):
        """
        Test GA-INT-003: Conditional automation based on state.
        
        Verify that automation sequence behaves differently based on game state.
        """
        # Create a conditional task that checks game state
        conditional_task = Task("Conditional Resource Collection", "collect")
        
        # Define a decision function based on game state
        def decide_collection_type(game_state):
            resources = {r["name"]: r["value"] for r in game_state["resources"]}
            
            # If gold is low, collect gold
            if resources.get("gold", 0) < 1500:
                return "gold"
            # If wood is low, collect wood
            elif resources.get("wood", 0) < 1000:
                return "wood"
            # Otherwise, collect stone
            else:
                return "stone"
        
        # Mock the execute method to check game state and behave accordingly
        def mock_execute(context=None):
            # Get current game state
            current_state = self.game_service.get_game_state()
            
            # Decide what to collect based on state
            resource_type = decide_collection_type(current_state)
            
            # Update game state with collected resource
            new_state = GameState.from_dict(current_state)
            
            # Add the collected resource
            for resource in new_state.get_resources():
                if resource["name"] == resource_type:
                    resource["value"] += 100
            
            # Update game state
            self.game_service.set_game_state(new_state)
            
            # Return result
            result = Task.Result()
            result.success = True
            result.status = TaskStatus.COMPLETED
            result.message = f"Collected 100 {resource_type}"
            return result
        
        conditional_task.execute = mock_execute
        
        # Execute the task in current state (gold should be collected)
        self.automation_service.execute_task(conditional_task)
        
        # Verify gold was collected (initial gold was 1000)
        updated_state = self.game_service.get_game_state()
        resources = {r["name"]: r["value"] for r in updated_state["resources"]}
        self.assertEqual(resources["gold"], 1100)  # 1000 + 100
        
        # Now modify state so wood would be collected next
        modified_state = GameState.from_dict(updated_state)
        for resource in modified_state.get_resources():
            if resource["name"] == "gold":
                resource["value"] = 2000  # High gold means wood should be collected next
        
        # Update game state
        self.game_service.set_game_state(modified_state)
        
        # Clear events
        self.received_events.clear()
        
        # Execute the task again
        self.automation_service.execute_task(conditional_task)
        
        # Verify wood was collected this time
        updated_state = self.game_service.get_game_state()
        resources = {r["name"]: r["value"] for r in updated_state["resources"]}
        self.assertEqual(resources["wood"], 600)  # 500 + 100
        
        # Verify events were published
        self.assertGreaterEqual(len(self.received_events), 2)
        
        # Find collection message
        collection_message = None
        for event in self.received_events:
            if event.type == EventType.TASK_COMPLETED and "message" in event.data:
                collection_message = event.data["message"]
                break
        
        self.assertIsNotNone(collection_message)
        self.assertIn("wood", collection_message.lower())

    def test_automation_sequence_execution(self):
        """
        Test automation sequence execution.
        
        Verify that multiple tasks can be executed in sequence.
        """
        # Create a sequence of tasks
        task_sequence = [
            self.create_mock_task("Collect Gold", "collect"),
            self.create_mock_task("Build House", "build"),
            self.create_mock_task("Train Worker", "train")
        ]
        
        # Execute the sequence
        self.automation_service.execute_sequence(task_sequence)
        
        # Allow time for sequence to execute
        time.sleep(0.5)
        
        # Verify all tasks were executed
        self.assertGreaterEqual(len(self.received_events), 6)  # 3 starts and 3 completions
        
        # Check task starts and completions
        task_starts = [e for e in self.received_events if e.type == EventType.TASK_STARTED]
        task_completions = [e for e in self.received_events if e.type == EventType.TASK_COMPLETED]
        
        self.assertEqual(len(task_starts), 3)
        self.assertEqual(len(task_completions), 3)
        
        # Check execution order
        task_start_names = [e.data.get("task_name") for e in task_starts]
        self.assertEqual(task_start_names, ["Collect Gold", "Build House", "Train Worker"])

    def test_error_handling_in_automation(self):
        """
        Test error handling in automation.
        
        Verify that errors in tasks are properly handled.
        """
        # Create a sequence with a failing task
        task_sequence = [
            self.create_mock_task("Collect Gold", "collect"),
            self.create_mock_task("Build House", "build", success=False),  # This task will fail
            self.create_mock_task("Train Worker", "train")
        ]
        
        # Execute the sequence with error handling
        self.automation_service.execute_sequence(task_sequence, continue_on_error=False)
        
        # Allow time for execution
        time.sleep(0.5)
        
        # Verify execution stopped at the failing task
        task_starts = [e for e in self.received_events if e.type == EventType.TASK_STARTED]
        task_completions = [e for e in self.received_events if e.type == EventType.TASK_COMPLETED]
        task_failures = [e for e in self.received_events if e.type == EventType.TASK_FAILED]
        
        self.assertEqual(len(task_starts), 2)  # Only first two tasks should start
        self.assertEqual(len(task_completions), 1)  # Only first task should complete
        self.assertEqual(len(task_failures), 1)  # Second task should fail
        
        # Verify third task was not executed
        task_start_names = [e.data.get("task_name") for e in task_starts]
        self.assertIn("Collect Gold", task_start_names)
        self.assertIn("Build House", task_start_names)
        self.assertNotIn("Train Worker", task_start_names)
        
        # Now try with continue_on_error=True
        self.received_events.clear()
        
        # Execute the sequence with error handling
        self.automation_service.execute_sequence(task_sequence, continue_on_error=True)
        
        # Allow time for execution
        time.sleep(0.5)
        
        # Verify all tasks were executed despite failure
        task_starts = [e for e in self.received_events if e.type == EventType.TASK_STARTED]
        task_completions = [e for e in self.received_events if e.type == EventType.TASK_COMPLETED]
        task_failures = [e for e in self.received_events if e.type == EventType.TASK_FAILED]
        
        self.assertEqual(len(task_starts), 3)  # All tasks should start
        self.assertEqual(len(task_completions), 2)  # First and third tasks should complete
        self.assertEqual(len(task_failures), 1)  # Second task should fail
        
        # Verify third task was executed
        task_start_names = [e.data.get("task_name") for e in task_starts]
        self.assertIn("Train Worker", task_start_names)

    def test_game_state_context_in_automation(self):
        """
        Test game state context in automation.
        
        Verify that tasks can access game state as context.
        """
        # Create a task that uses game state context
        context_task = Task("Context-Aware Task", "context")
        
        # Track context received by the task
        received_context = None
        
        # Mock the execute method
        def mock_execute(context=None):
            nonlocal received_context
            received_context = context
            
            # Return success
            result = Task.Result()
            result.success = True
            result.status = TaskStatus.COMPLETED
            return result
        
        context_task.execute = mock_execute
        
        # Execute task with game state as context
        game_state = self.game_service.get_game_state()
        self.automation_service.execute_task(context_task, context=game_state)
        
        # Verify task received game state as context
        self.assertIsNotNone(received_context)
        self.assertIn("resources", received_context)
        self.assertIn("buildings", received_context)
        self.assertIn("units", received_context)
        
        # Verify context contains correct data
        resources = {r["name"]: r["value"] for r in received_context["resources"]}
        self.assertEqual(resources["gold"], 1000)
        self.assertEqual(resources["wood"], 500)
        self.assertEqual(resources["stone"], 200)


if __name__ == "__main__":
    unittest.main() 