"""
Main Controller

This module provides the main controller for the Scout application.
It coordinates actions between the UI and the service layer.
"""

import logging
from typing import Dict, List, Optional, Any
import os
import json

from scout.core.window.window_service_interface import WindowServiceInterface
from scout.core.detection.detection_service_interface import DetectionServiceInterface
from scout.core.game.game_service_interface import GameServiceInterface
from scout.core.automation.automation_service_interface import AutomationServiceInterface
from scout.ui.models.settings_model import SettingsModel

# Set up logging
logger = logging.getLogger(__name__)

class MainController:
    """
    Main controller for the Scout application.
    
    This class is responsible for:
    - Coordinating actions between the UI and the service layer
    - Managing application state
    - Processing user commands from the UI
    - Routing events between services and UI components
    - Handling configuration and settings
    
    It follows the MVC pattern, serving as the controller component that
    connects views (UI) with models (services and data).
    """
    
    def __init__(self, 
                window_service: WindowServiceInterface,
                detection_service: DetectionServiceInterface,
                game_service: GameServiceInterface,
                automation_service: AutomationServiceInterface,
                settings_model: SettingsModel):
        """
        Initialize the main controller.
        
        Args:
            window_service: Service for window management
            detection_service: Service for detection operations
            game_service: Service for game state management
            automation_service: Service for automation operations
            settings_model: Model for application settings
        """
        self.window_service = window_service
        self.detection_service = detection_service
        self.game_service = game_service
        self.automation_service = automation_service
        self.settings_model = settings_model
        
        # Initialize controller state
        self._active_view = None
        self._running_tasks = set()
        
        # Load settings
        self._load_settings()
        
        logger.info("Main controller initialized")
    
    def _load_settings(self) -> None:
        """Load application settings."""
        self.settings_model.load()
        
        # Apply window title setting if available
        window_title = self.settings_model.get('window_title')
        if window_title:
            self.window_service.set_window_title(window_title)
    
    def save_settings(self) -> None:
        """Save application settings."""
        self.settings_model.save()
        logger.info("Settings saved")
    
    def find_game_window(self) -> bool:
        """
        Find the game window using the window service.
        
        Returns:
            True if the window was found, False otherwise
        """
        # Get the window title from settings
        window_title = self.settings_model.get('window_title', 'Total Battle')
        
        # Try to find the window
        self.window_service.set_window_title(window_title)
        found = self.window_service.find_window()
        
        if found:
            logger.info(f"Found game window with title: {window_title}")
            
            # Update detection service context
            self.detection_service.set_context({
                'window_title': window_title
            })
        else:
            logger.warning(f"Could not find game window with title: {window_title}")
            
        return found
    
    def run_detection(self, strategy: str, params: Dict) -> List[Dict]:
        """
        Run a detection operation.
        
        Args:
            strategy: Detection strategy to use (template, ocr, yolo)
            params: Parameters for the detection operation
            
        Returns:
            List of detection results
        """
        # Ensure window is available
        if not self.window_service.is_window_available():
            if not self.find_game_window():
                logger.error("Cannot run detection - game window not found")
                return []
        
        # Run detection based on strategy
        results = []
        
        try:
            if strategy == 'template':
                template_name = params.get('template_name')
                confidence = params.get('confidence_threshold', 0.7)
                max_results = params.get('max_results', 10)
                region = params.get('region')
                
                results = self.detection_service.detect_template(
                    template_name=template_name,
                    confidence_threshold=confidence,
                    max_results=max_results,
                    region=region
                )
                
            elif strategy == 'ocr':
                pattern = params.get('pattern')
                confidence = params.get('confidence_threshold', 0.6)
                region = params.get('region')
                preprocess = params.get('preprocess')
                
                results = self.detection_service.detect_text(
                    pattern=pattern,
                    confidence_threshold=confidence,
                    region=region,
                    preprocess=preprocess
                )
                
            elif strategy == 'yolo':
                class_names = params.get('class_names')
                confidence = params.get('confidence_threshold', 0.5)
                region = params.get('region')
                
                results = self.detection_service.detect_objects(
                    class_names=class_names,
                    confidence_threshold=confidence,
                    region=region
                )
                
            else:
                logger.warning(f"Unsupported detection strategy: {strategy}")
                
        except Exception as e:
            logger.error(f"Error running detection: {e}")
            
        return results
    
    def execute_automation_task(self, task_type: str, params: Dict) -> bool:
        """
        Execute an automation task.
        
        Args:
            task_type: Type of task to execute
            params: Parameters for the task
            
        Returns:
            True if the task was successfully started, False otherwise
        """
        # Ensure window is available
        if not self.window_service.is_window_available():
            if not self.find_game_window():
                logger.error("Cannot execute task - game window not found")
                return False
        
        try:
            # Create and execute the task
            task = self.automation_service.create_task(task_type, **params)
            self.automation_service.schedule_task(task)
            
            # Add to running tasks
            self._running_tasks.add(task.id)
            
            logger.info(f"Scheduled automation task: {task_type} (ID: {task.id})")
            return True
            
        except Exception as e:
            logger.error(f"Error executing automation task: {e}")
            return False
    
    def stop_automation(self) -> None:
        """Stop all automation tasks."""
        self.automation_service.stop_execution()
        self._running_tasks.clear()
        logger.info("Stopped all automation tasks")
    
    def pause_automation(self) -> None:
        """Pause automation execution."""
        self.automation_service.pause_execution()
        logger.info("Paused automation execution")
    
    def resume_automation(self) -> None:
        """Resume automation execution."""
        self.automation_service.resume_execution()
        logger.info("Resumed automation execution")
    
    def save_game_state(self, file_path: Optional[str] = None) -> bool:
        """
        Save the current game state.
        
        Args:
            file_path: Path to save the state to (None for default location)
            
        Returns:
            True if the state was saved successfully, False otherwise
        """
        try:
            self.game_service.save_state(file_path)
            logger.info(f"Saved game state to {file_path or 'default location'}")
            return True
        except Exception as e:
            logger.error(f"Error saving game state: {e}")
            return False
    
    def load_game_state(self, file_path: Optional[str] = None) -> bool:
        """
        Load a game state from a file.
        
        Args:
            file_path: Path to load the state from (None for default location)
            
        Returns:
            True if the state was loaded successfully, False otherwise
        """
        try:
            self.game_service.load_state(file_path)
            logger.info(f"Loaded game state from {file_path or 'default location'}")
            return True
        except Exception as e:
            logger.error(f"Error loading game state: {e}")
            return False
    
    def update_game_resources(self, resource_type: str, amount: int) -> None:
        """
        Update a resource amount in the game state.
        
        Args:
            resource_type: Type of resource to update
            amount: New amount of the resource
        """
        try:
            self.game_service.update_resource(resource_type, amount)
            logger.info(f"Updated {resource_type} resource to {amount}")
        except Exception as e:
            logger.error(f"Error updating game resource: {e}")
    
    def add_entity_to_game_state(self, entity_type: str, entity_data: Dict) -> None:
        """
        Add an entity to the game state.
        
        Args:
            entity_type: Type of entity to add
            entity_data: Entity data
        """
        try:
            self.game_service.add_entity(entity_type, entity_data)
            logger.info(f"Added {entity_type} entity to game state")
        except Exception as e:
            logger.error(f"Error adding entity to game state: {e}")
    
    def clear_detection_cache(self) -> None:
        """Clear the detection cache."""
        self.detection_service.clear_cache()
        logger.info("Cleared detection cache")
    
    def set_active_view(self, view_name: str) -> None:
        """
        Set the active view for coordination.
        
        Args:
            view_name: Name of the active view
        """
        self._active_view = view_name
        logger.debug(f"Active view set to: {view_name}")
    
    def get_settings(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value.
        
        Args:
            key: Setting key
            default: Default value if the setting doesn't exist
            
        Returns:
            Setting value or default
        """
        return self.settings_model.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> None:
        """
        Set a setting value.
        
        Args:
            key: Setting key
            value: Setting value
        """
        self.settings_model.set(key, value)
        logger.debug(f"Setting updated: {key}={value}")
    
    def load_automation_sequence(self, file_path: str) -> Dict:
        """
        Load an automation sequence from a file.
        
        Args:
            file_path: Path to the sequence file
            
        Returns:
            Sequence data or empty dict if failed
        """
        try:
            with open(file_path, 'r') as f:
                sequence = json.load(f)
            logger.info(f"Loaded automation sequence from {file_path}")
            return sequence
        except Exception as e:
            logger.error(f"Error loading automation sequence: {e}")
            return {}
    
    def save_automation_sequence(self, sequence: Dict, file_path: str) -> bool:
        """
        Save an automation sequence to a file.
        
        Args:
            sequence: Sequence data to save
            file_path: Path to save the sequence to
            
        Returns:
            True if the sequence was saved successfully, False otherwise
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(sequence, f, indent=4)
            logger.info(f"Saved automation sequence to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving automation sequence: {e}")
            return False
    
    def execute_automation_sequence(self, sequence: Dict) -> bool:
        """
        Execute an automation sequence.
        
        Args:
            sequence: Sequence data to execute
            
        Returns:
            True if the sequence was successfully started, False otherwise
        """
        try:
            # Convert sequence to tasks
            tasks = []
            for task_data in sequence.get('tasks', []):
                task_type = task_data.get('type')
                task_params = task_data.get('params', {})
                
                task = self.automation_service.create_task(task_type, **task_params)
                tasks.append(task)
                
            # Schedule tasks with dependencies if specified
            for i, task_data in enumerate(sequence.get('tasks', [])):
                dependencies = task_data.get('dependencies', [])
                if dependencies and i < len(tasks):
                    for dep_idx in dependencies:
                        if 0 <= dep_idx < len(tasks):
                            tasks[i].add_dependency(tasks[dep_idx])
            
            # Schedule the tasks
            for task in tasks:
                self.automation_service.schedule_task(task)
                
            # Start execution
            self.automation_service.start_execution()
            
            logger.info(f"Started automation sequence with {len(tasks)} tasks")
            return True
            
        except Exception as e:
            logger.error(f"Error executing automation sequence: {e}")
            return False 