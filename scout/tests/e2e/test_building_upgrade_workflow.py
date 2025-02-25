"""
Building Upgrade End-to-End Test

This module contains comprehensive end-to-end tests for the building upgrade
workflow in the Total Battle game. It simulates a complete workflow where the
application identifies buildings, checks upgrade requirements, and performs
the upgrade process.
"""

import unittest
import os
import tempfile
import shutil
import time
import logging
import cv2
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from scout.core.events.event_bus import EventBus
from scout.core.events.event_types import EventType
from scout.core.window.window_service import WindowService
from scout.core.detection.detection_service import DetectionService
from scout.core.detection.strategies.template_strategy import TemplateMatchingStrategy
from scout.core.detection.strategies.ocr_strategy import OCRStrategy
from scout.core.game.game_service import GameService
from scout.core.game.game_state import Coordinates, Building, Resource
from scout.core.automation.automation_service import AutomationService
from scout.core.automation.task import TaskStatus, CompositeTask
from scout.core.automation.tasks.basic_tasks import ClickTask, WaitTask, DetectTask
from scout.core.automation.tasks.game_tasks import NavigateToCoordinatesTask

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MockActionsService:
    """Mock implementation of an actions service for testing."""
    
    def __init__(self):
        self.actions_log = []
    
    def click_at(self, x, y, relative_to_window=True, button='left', clicks=1):
        """Log click actions."""
        self.actions_log.append(('click', x, y, relative_to_window, button, clicks))
        logger.debug(f"Clicked at ({x}, {y})")
        return True
    
    def drag_mouse(self, start_x, start_y, end_x, end_y, relative_to_window=True, duration=0.5):
        """Log drag actions."""
        self.actions_log.append(('drag', start_x, start_y, end_x, end_y, relative_to_window, duration))
        logger.debug(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")
        return True
    
    def input_text(self, text):
        """Log text input actions."""
        self.actions_log.append(('input_text', text))
        logger.debug(f"Typed text: '{text}'")
        return True
    
    def get_actions(self):
        """Get all logged actions."""
        return self.actions_log
    
    def clear_log(self):
        """Clear action log."""
        self.actions_log = []


class BuildingUpgradeWorkflowTest(unittest.TestCase):
    """
    End-to-end test for the building upgrade workflow.
    
    This test simulates the complete process of:
    1. Finding buildings in the city
    2. Selecting a building to upgrade
    3. Checking resource requirements
    4. Initiating the upgrade process
    5. Verifying the building is being upgraded
    
    It verifies that all components of the system work together to
    automate a complete real-world scenario.
    """
    
    def setUp(self):
        """Set up test environment."""
        # Create shared event bus
        self.event_bus = EventBus()
        
        # Create temporary directory for templates and state
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = os.path.join(self.temp_dir, 'templates')
        self.state_dir = os.path.join(self.temp_dir, 'state')
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.state_dir, exist_ok=True)
        
        # Create test template images
        self._create_test_templates()
        
        # Create test city layout
        self.city_buildings = self._create_city_layout()
        
        # Initialize core services
        self._init_services()
        
        # Set up initial game state for testing
        self._setup_initial_game_state()
    
    def tearDown(self):
        """Clean up after test."""
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir)
    
    def _create_test_templates(self):
        """Create test template images for building detection."""
        # Create building templates
        building_types = [
            ("barracks", (90, 30, 200)),  # Red building
            ("farm", (70, 150, 50)),      # Green building
            ("town_hall", (200, 150, 100)), # Brown building
            ("mine", (120, 120, 120)),    # Gray building
            ("warehouse", (150, 80, 40))  # Brown building
        ]
        
        for name, color in building_types:
            # Create building template
            building_path = os.path.join(self.templates_dir, f'{name}.png')
            building_img = np.zeros((60, 60, 3), dtype=np.uint8)
            building_img[:, :] = color  # BGR color
            
            # Add some distinguishing features
            if name == "barracks":
                # Add flag on top
                cv2.rectangle(building_img, (25, 5), (35, 15), (0, 0, 255), -1)
            elif name == "farm":
                # Add crop rows
                for i in range(3):
                    cv2.line(building_img, (10, 20 + i*10), (50, 20 + i*10), (0, 255, 0), 2)
            elif name == "town_hall":
                # Add dome roof
                cv2.circle(building_img, (30, 15), 15, (150, 100, 50), -1)
            elif name == "mine":
                # Add entrance
                cv2.rectangle(building_img, (20, 40), (40, 59), (50, 50, 50), -1)
            elif name == "warehouse":
                # Add door
                cv2.rectangle(building_img, (25, 40), (35, 59), (100, 50, 25), -1)
                
            cv2.imwrite(building_path, building_img)
        
        # Create upgrade button template
        upgrade_path = os.path.join(self.templates_dir, 'upgrade_button.png')
        upgrade_img = np.zeros((50, 120, 3), dtype=np.uint8)
        upgrade_img[:, :] = (50, 150, 50)  # Green button
        cv2.putText(upgrade_img, "Upgrade", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imwrite(upgrade_path, upgrade_img)
        
        # Create close button template
        close_path = os.path.join(self.templates_dir, 'close_button.png')
        close_img = np.zeros((30, 30, 3), dtype=np.uint8)
        close_img[:, :] = (50, 50, 200)  # Red button
        cv2.line(close_img, (5, 5), (25, 25), (255, 255, 255), 2)
        cv2.line(close_img, (5, 25), (25, 5), (255, 255, 255), 2)
        cv2.imwrite(close_path, close_img)
        
        # Create resource cost indicator template
        resource_cost_path = os.path.join(self.templates_dir, 'resource_cost.png')
        resource_cost_img = np.zeros((30, 100, 3), dtype=np.uint8)
        resource_cost_img[:, :] = (150, 150, 150)  # Gray background
        cv2.putText(resource_cost_img, "1000 Gold", (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.imwrite(resource_cost_path, resource_cost_img)
    
    def _create_city_layout(self):
        """Create a virtual city layout with buildings."""
        # Define buildings in the city
        buildings = [
            {"type": "town_hall", "level": 5, "position": (400, 300), "size": (80, 80)},
            {"type": "barracks", "level": 3, "position": (200, 250), "size": (60, 60)},
            {"type": "farm", "level": 4, "position": (550, 200), "size": (60, 60)},
            {"type": "mine", "level": 2, "position": (300, 400), "size": (60, 60)},
            {"type": "warehouse", "level": 3, "position": (500, 350), "size": (60, 60)}
        ]
        
        # Return the city layout
        return buildings
    
    def _init_services(self):
        """Initialize all services required for testing."""
        # Create window service (mocked)
        self.window_service = WindowService(self.event_bus)
        self.window_service.find_window = MagicMock(return_value=True)
        self.window_service.get_window_position = MagicMock(return_value=(0, 0, 800, 600))
        
        # Create city view
        self._update_city_view()
        
        # Create detection service with template strategy
        self.detection_service = DetectionService(self.event_bus, self.window_service)
        template_strategy = TemplateMatchingStrategy(templates_dir=self.templates_dir)
        self.detection_service.register_strategy('template', template_strategy)
        
        # Mock OCR strategy for resource costs
        ocr_strategy = MagicMock(spec=OCRStrategy)
        
        # Configure OCR mock to return predefined results
        def mock_detect(image, **kwargs):
            # Convert detected text to resource costs
            region = kwargs.get('region', {})
            
            # If detecting in resource cost region
            if region.get('top', 0) > 300 and region.get('left', 0) > 300:
                return [
                    {
                        'text': 'Gold: 1000',
                        'confidence': 0.95,
                        'x': region.get('left', 0) + 10,
                        'y': region.get('top', 0) + 10,
                        'width': 100,
                        'height': 20
                    },
                    {
                        'text': 'Wood: 500',
                        'confidence': 0.93,
                        'x': region.get('left', 0) + 10,
                        'y': region.get('top', 0) + 35,
                        'width': 100,
                        'height': 20
                    }
                ]
            return []
            
        ocr_strategy.detect = mock_detect
        ocr_strategy.get_name.return_value = 'ocr'
        self.detection_service.register_strategy('ocr', ocr_strategy)
        
        # Create game service
        self.game_service = GameService(
            self.event_bus,
            self.detection_service,
            state_file_path=os.path.join(self.state_dir, 'game_state.json')
        )
        
        # Create actions service (mocked)
        self.actions_service = MockActionsService()
        
        # Create automation service
        self.automation_service = AutomationService(self.event_bus)
        
        # Set up execution context
        self.automation_service.set_execution_context({
            'window_service': self.window_service,
            'detection_service': self.detection_service,
            'game_service': self.game_service,
            'actions_service': self.actions_service
        })
        
        # Hook building interaction
        self._hook_building_interaction()
    
    def _hook_building_interaction(self):
        """
        Hook into building interaction to update the game view.
        
        When buildings are clicked, we need to update our simulated game view
        to show the building details and upgrade options.
        """
        # Store original method
        self._original_click = self.actions_service.click_at
        
        # Override click method to check for building clicks
        def mock_click(x, y, relative_to_window=True, button='left', clicks=1):
            result = self._original_click(x, y, relative_to_window, button, clicks)
            
            # Check if clicking on a building
            for building in self.city_buildings:
                bx, by = building["position"]
                bw, bh = building["size"]
                
                if (bx - bw//2 <= x <= bx + bw//2 and 
                    by - bh//2 <= y <= by + bh//2):
                    # We clicked on this building - update the view to show building details
                    self.selected_building = building
                    self._update_city_view(show_building_details=True)
                    logger.info(f"Selected building: {building['type']} (Level {building['level']})")
                    return result
            
            # Check if clicking upgrade button (only active when building details shown)
            if (hasattr(self, 'selected_building') and 
                350 <= x <= 450 and 
                400 <= y <= 450):
                # We clicked the upgrade button - initiate upgrade
                if self._can_upgrade_building():
                    # Update building level and set construction time
                    self.selected_building["level"] += 1
                    self._update_city_view(show_building_details=False)
                    
                    # Deduct resources
                    gold = self.game_service.state.resources.get("gold")
                    wood = self.game_service.state.resources.get("wood")
                    self.game_service.state.resources.update("gold", gold.amount - 1000, gold.capacity)
                    self.game_service.state.resources.update("wood", wood.amount - 500, wood.capacity)
                    
                    # Set building to upgrading state
                    building_name = self.selected_building["type"]
                    self.game_service.state.buildings[building_name].level = self.selected_building["level"]
                    self.game_service.state.buildings[building_name].construction_time = (
                        datetime.now() + timedelta(minutes=5)  # Simulate 5 minute upgrade time
                    )
                    
                    logger.info(f"Started upgrade of {building_name} to level {self.selected_building['level']}")
                else:
                    logger.info("Cannot upgrade building - insufficient resources")
                
                return result
            
            # Check if clicking close button
            if (hasattr(self, 'selected_building') and 
                500 <= x <= 530 and 
                150 <= y <= 180):
                # We clicked the close button - close building details
                if hasattr(self, 'selected_building'):
                    del self.selected_building
                self._update_city_view(show_building_details=False)
                logger.info("Closed building details")
                return result
                
            return result
            
        # Apply our mock function
        self.actions_service.click_at = mock_click
    
    def _can_upgrade_building(self):
        """Check if the selected building can be upgraded."""
        # Check resource requirements
        gold = self.game_service.state.resources.get("gold")
        wood = self.game_service.state.resources.get("wood")
        
        return gold.amount >= 1000 and wood.amount >= 500
    
    def _update_city_view(self, show_building_details=False):
        """
        Update the simulated game view to show the city.
        
        Args:
            show_building_details: Whether to show the building details panel
        """
        # Create base city view image (800x600)
        city_view = np.zeros((600, 800, 3), dtype=np.uint8)
        
        # Add background (light brown terrain)
        city_view[:, :] = (120, 180, 200)
        
        # Add coordinate display at top left
        cv2.putText(
            city_view, 
            "City View", 
            (20, 30), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.7, 
            (255, 255, 255), 
            2
        )
        
        # Add buildings to the view
        for building in self.city_buildings:
            btype = building["type"]
            level = building["level"]
            x, y = building["position"]
            w, h = building["size"]
            
            # Set building color based on type
            if btype == "barracks":
                color = (90, 30, 200)  # Red
            elif btype == "farm":
                color = (70, 150, 50)  # Green
            elif btype == "town_hall":
                color = (200, 150, 100)  # Brown
            elif btype == "mine":
                color = (120, 120, 120)  # Gray
            elif btype == "warehouse":
                color = (150, 80, 40)  # Brown
            else:
                color = (200, 200, 200)  # Default gray
            
            # Draw building
            cv2.rectangle(
                city_view,
                (x - w//2, y - h//2),
                (x + w//2, y + h//2),
                color,
                -1
            )
            
            # Add level indicator
            cv2.putText(
                city_view,
                f"Lv{level}",
                (x - 15, y + 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1
            )
            
            # If this is the selected building, add highlight
            if (show_building_details and 
                hasattr(self, 'selected_building') and 
                self.selected_building["type"] == btype):
                cv2.rectangle(
                    city_view,
                    (x - w//2 - 5, y - h//2 - 5),
                    (x + w//2 + 5, y + h//2 + 5),
                    (0, 255, 255),  # Yellow highlight
                    2
                )
        
        # Add building details panel if needed
        if show_building_details and hasattr(self, 'selected_building'):
            # Add panel background
            cv2.rectangle(
                city_view,
                (300, 150),
                (550, 450),
                (50, 50, 50),  # Dark gray
                -1
            )
            
            # Add building name
            cv2.putText(
                city_view,
                f"{self.selected_building['type'].replace('_', ' ').title()}",
                (320, 180),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )
            
            # Add level
            cv2.putText(
                city_view,
                f"Level {self.selected_building['level']}",
                (320, 210),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1
            )
            
            # Add resource requirements for upgrade
            cv2.putText(
                city_view,
                "Upgrade Cost:",
                (320, 240),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1
            )
            
            cv2.putText(
                city_view,
                "Gold: 1000",
                (320, 270),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (200, 200, 50),  # Gold color
                1
            )
            
            cv2.putText(
                city_view,
                "Wood: 500",
                (320, 300),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (50, 100, 150),  # Wood color
                1
            )
            
            # Add upgrade button
            button_color = (50, 150, 50) if self._can_upgrade_building() else (50, 50, 150)
            cv2.rectangle(
                city_view,
                (350, 400),
                (450, 450),
                button_color,  # Green if can upgrade, otherwise blue
                -1
            )
            
            cv2.putText(
                city_view,
                "Upgrade",
                (360, 430),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )
            
            # Add close button
            cv2.rectangle(
                city_view,
                (500, 150),
                (530, 180),
                (50, 50, 200),  # Red
                -1
            )
            
            cv2.line(
                city_view,
                (505, 155),
                (525, 175),
                (255, 255, 255),
                2
            )
            
            cv2.line(
                city_view,
                (505, 175),
                (525, 155),
                (255, 255, 255),
                2
            )
        
        # Update the window service to return this view
        self.window_service.capture_screenshot = MagicMock(return_value=city_view)
    
    def _setup_initial_game_state(self):
        """Set up initial game state for testing."""
        # Set current position to city position
        self.game_service.state.current_position = Coordinates(1, 100, 100)
        
        # Add resources to player inventory
        self.game_service.state.resources.update("gold", 5000, 10000)
        self.game_service.state.resources.update("wood", 2500, 5000)
        self.game_service.state.resources.update("stone", 1000, 2000)
        
        # Add buildings to game state
        for building_data in self.city_buildings:
            building = Building(
                name=building_data["type"],
                level=building_data["level"]
            )
            self.game_service.state.buildings[building_data["type"]] = building
        
        # Save state
        self.game_service.save_state()
    
    def test_building_upgrade_workflow(self):
        """
        Test complete building upgrade workflow.
        
        This tests the following workflow:
        1. Detect buildings in the city
        2. Select a building to upgrade
        3. Check resource requirements
        4. Initiate the upgrade process
        5. Verify the building is being upgraded
        """
        # Record initial resource amounts
        initial_gold = self.game_service.state.resources.get("gold").amount
        initial_wood = self.game_service.state.resources.get("wood").amount
        
        # Record initial building levels
        initial_levels = {}
        for name, building in self.game_service.state.buildings.items():
            initial_levels[name] = building.level
        
        # Step 1: Detect buildings in the city
        logger.info("Step 1: Detecting buildings in the city")
        detect_buildings_task = DetectTask(
            "detect_buildings",
            strategy="template",
            templates=["barracks", "farm", "town_hall", "mine", "warehouse"],
            confidence=0.7
        )
        
        # Execute detection task
        self.automation_service.execute_task_synchronously(detect_buildings_task)
        
        # Verify detection task completed successfully
        self.assertEqual(detect_buildings_task.status, TaskStatus.COMPLETED)
        
        # Verify buildings were detected
        detected_buildings = detect_buildings_task.result
        self.assertGreater(len(detected_buildings), 0)
        logger.info(f"Detected {len(detected_buildings)} buildings")
        
        # Step 2: Select a building to upgrade (barracks for this test)
        target_building = None
        for building in detected_buildings:
            if building["template_name"] == "barracks":
                target_building = building
                break
                
        self.assertIsNotNone(target_building, "Barracks not found")
        
        # Click on the barracks building
        logger.info("Step 2: Selecting barracks for upgrade")
        click_building_task = ClickTask(
            "click_barracks",
            target_building["x"] + target_building["width"] // 2,
            target_building["y"] + target_building["height"] // 2
        )
        
        self.automation_service.execute_task_synchronously(click_building_task)
        self.assertEqual(click_building_task.status, TaskStatus.COMPLETED)
        
        # Step 3: Detect and verify upgrade requirements
        logger.info("Step 3: Checking upgrade requirements")
        detect_requirements_task = DetectTask(
            "detect_requirements",
            strategy="ocr",
            region={"left": 300, "top": 240, "width": 250, "height": 100}
        )
        
        self.automation_service.execute_task_synchronously(detect_requirements_task)
        self.assertEqual(detect_requirements_task.status, TaskStatus.COMPLETED)
        
        # Verify resource requirements were detected
        resource_texts = [
            result["text"] for result in detect_requirements_task.result or []
            if "gold" in result["text"].lower() or "wood" in result["text"].lower()
        ]
        
        self.assertGreater(len(resource_texts), 0, "Resource requirements not found")
        logger.info(f"Detected resource requirements: {resource_texts}")
        
        # Step 4: Detect and click the upgrade button
        logger.info("Step 4: Initiating building upgrade")
        detect_upgrade_button_task = DetectTask(
            "detect_upgrade_button",
            strategy="template",
            templates=["upgrade_button"]
        )
        
        self.automation_service.execute_task_synchronously(detect_upgrade_button_task)
        self.assertEqual(detect_upgrade_button_task.status, TaskStatus.COMPLETED)
        
        # Verify upgrade button was found
        upgrade_buttons = detect_upgrade_button_task.result
        self.assertGreater(len(upgrade_buttons), 0, "Upgrade button not found")
        
        # Click the upgrade button
        upgrade_button = upgrade_buttons[0]
        click_upgrade_task = ClickTask(
            "click_upgrade",
            upgrade_button["x"] + upgrade_button["width"] // 2,
            upgrade_button["y"] + upgrade_button["height"] // 2
        )
        
        self.automation_service.execute_task_synchronously(click_upgrade_task)
        self.assertEqual(click_upgrade_task.status, TaskStatus.COMPLETED)
        
        # Step 5: Verify upgrade was initiated
        logger.info("Step 5: Verifying upgrade initiated")
        
        # Check if resources were spent
        final_gold = self.game_service.state.resources.get("gold").amount
        final_wood = self.game_service.state.resources.get("wood").amount
        
        self.assertLess(final_gold, initial_gold, "Gold not spent on upgrade")
        self.assertLess(final_wood, initial_wood, "Wood not spent on upgrade")
        
        logger.info(f"Resources spent - Gold: {initial_gold - final_gold}, Wood: {initial_wood - final_wood}")
        
        # Check if barracks is being upgraded
        barracks = self.game_service.state.buildings.get("barracks")
        self.assertIsNotNone(barracks)
        self.assertGreater(barracks.level, initial_levels["barracks"], "Barracks level not increased")
        self.assertTrue(barracks.is_upgrading(), "Barracks not in upgrading state")
        
        # Log completion
        logger.info(f"Building upgrade workflow completed - Barracks now level {barracks.level}")
        logger.info(f"Upgrade will complete in {barracks.time_remaining()} seconds")


if __name__ == '__main__':
    unittest.main() 