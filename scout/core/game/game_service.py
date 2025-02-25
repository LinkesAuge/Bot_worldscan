"""
Game Service

This module provides the GameService class which is responsible for managing and
updating the game state by integrating with the Detection Service. It processes
information from screenshots to build and maintain a model of the game world.
"""

from typing import Dict, List, Optional, Tuple, Any, Set
import logging
import time
from datetime import datetime, timedelta
import re
import json
import os
from pathlib import Path

from ..design.singleton import Singleton
from ..events.event_bus import EventBus
from ..events.event import Event
from ..events.event_types import EventType
from ..window.window_service_interface import WindowServiceInterface
from ..detection.detection_service_interface import DetectionServiceInterface
from .game_service_interface import GameServiceInterface
from .game_state import (
    GameState, Coordinates, Resource, Resources, Building, Army, MapEntity
)

logger = logging.getLogger(__name__)

class GameService(GameServiceInterface):
    """
    Service for managing the game state.
    
    This service:
    - Uses the Detection Service to extract information from game screenshots
    - Updates the game state based on detected information
    - Provides methods for querying and manipulating the game state
    - Publishes events when significant game state changes occur
    - Persists and loads game state to/from disk
    """
    
    # Use a class variable for the singleton instance
    _instance = None
    
    # Override the __new__ method for singleton pattern
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(GameService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self, 
        window_service: WindowServiceInterface,
        detection_service: DetectionServiceInterface,
        event_bus: EventBus,
        state_file_path: Optional[str] = None
    ):
        """
        Initialize the game service.
        
        Args:
            window_service: Service for capturing screenshots
            detection_service: Service for detecting game elements
            event_bus: Service for publishing/subscribing to events
            state_file_path: Path to save/load game state (optional)
        """
        # Only initialize once
        if getattr(self, '_initialized', False):
            return
            
        self._initialized = True
        self._window_service = window_service
        self._detection_service = detection_service
        self._event_bus = event_bus
        self._state_file_path = state_file_path
        self._game_state = GameState()
        self._last_update = time.time()
        self._detection_regions: Dict[str, Dict[str, int]] = {}
        
        # Subscribe to detection events
        self._event_bus.subscribe(EventType.DETECTION_COMPLETED, self._on_detection_completed)
        
        logger.info("Game service initialized")
        
        # Load state from file if available
        if state_file_path:
            self._load_state()
    
    @property
    def state(self) -> GameState:
        """
        Get the current game state.
        
        Returns:
            The current GameState
        """
        return self._game_state
    
    def configure_detection_regions(self, regions: Dict[str, Dict[str, int]]) -> None:
        """
        Configure detection regions for different game elements.
        
        Args:
            regions: Dictionary mapping region name to bounding box
        """
        self._detection_regions.update(regions)
        logger.debug(f"Updated detection regions: {regions.keys()}")
    
    def update_state(self, force_detection: bool = False) -> None:
        """
        Update the game state by performing detections.
        
        This method:
        1. Captures the current game view
        2. Detects game elements using the Detection Service
        3. Updates the game state based on detected elements
        
        Args:
            force_detection: Whether to bypass caching in the Detection Service
        """
        try:
            # Update coordinates
            self._update_coordinates(force_detection)
            
            # Update resources
            self._update_resources(force_detection)
            
            # Update timestamp
            self._game_state.update_timestamp()
            
            # Save state
            self._save_state()
            
            # Publish event
            self._publish_state_changed_event()
            
        except Exception as e:
            logger.error(f"Error updating game state: {e}")
    
    def _update_coordinates(self, force_detection: bool = False) -> None:
        """
        Update player coordinates from game view.
        
        Args:
            force_detection: Whether to bypass caching
        """
        # Skip if coordinates region not configured
        if 'coordinates' not in self._detection_regions:
            return
            
        # Detect text in coordinates region
        region = self._detection_regions['coordinates']
        text = self._detection_service.get_text(
            region=region,
            preprocess='thresh'
        )
        
        if not text:
            logger.debug("No text detected in coordinates region")
            return
            
        # Extract coordinates using regex
        coords = self._parse_coordinates(text)
        if coords:
            kingdom, x, y = coords
            self._game_state.current_position = Coordinates(kingdom, x, y)
            logger.debug(f"Updated player coordinates: {self._game_state.current_position}")
            
            # Add to explored coordinates
            self._game_state.explored_coordinates.add(self._game_state.current_position)
        else:
            logger.debug(f"Failed to parse coordinates from text: {text}")
    
    def _update_resources(self, force_detection: bool = False) -> None:
        """
        Update resource information from game view.
        
        Args:
            force_detection: Whether to bypass caching
        """
        # Skip if resources region not configured
        if 'resources' not in self._detection_regions:
            return
            
        # Detect text in resources region
        region = self._detection_regions['resources']
        text = self._detection_service.get_text(
            region=region,
            preprocess='thresh'
        )
        
        if not text:
            logger.debug("No text detected in resources region")
            return
            
        # Parse resources - this is a simplistic approach, would need
        # to be refined based on actual game UI
        self._parse_resources(text)
    
    def _parse_coordinates(self, text: str) -> Optional[Tuple[int, int, int]]:
        """
        Parse coordinates from text.
        
        Args:
            text: Text to parse
            
        Returns:
            Tuple of (kingdom, x, y) if found, None otherwise
        """
        # Look for patterns like "K:1 X:123 Y:456" or variations
        k_match = re.search(r'K:?\s*(\d+)', text)
        x_match = re.search(r'X:?\s*(\d+)', text)
        y_match = re.search(r'Y:?\s*(\d+)', text)
        
        if k_match and x_match and y_match:
            try:
                kingdom = int(k_match.group(1))
                x = int(x_match.group(1))
                y = int(y_match.group(1))
                
                # Simple validation
                if 0 <= kingdom <= 99 and 0 <= x <= 999 and 0 <= y <= 999:
                    return (kingdom, x, y)
                    
            except ValueError:
                pass
                
        return None
    
    def _parse_resources(self, text: str) -> None:
        """
        Parse resource information from text.
        
        Args:
            text: Text to parse for resource information
        """
        # This is a simplified example - real implementation would depend
        # on the exact format of resource display in the game
        for resource_name in ['gold', 'food', 'wood', 'stone', 'iron', 'crystal']:
            # Look for patterns like "Gold: 123,456/200,000"
            pattern = fr'{resource_name.capitalize()}:?\s*([0-9,]+)(?:/([0-9,]+))?'
            match = re.search(pattern, text, re.IGNORECASE)
            
            if match:
                try:
                    # Parse amount and capacity
                    amount_str = match.group(1).replace(',', '')
                    amount = int(amount_str)
                    
                    capacity = None
                    if match.group(2):
                        capacity_str = match.group(2).replace(',', '')
                        capacity = int(capacity_str)
                    
                    # Update resource
                    self._game_state.resources.update(resource_name, amount, capacity)
                    logger.debug(f"Updated resource {resource_name}: {amount}/{capacity}")
                    
                except ValueError:
                    logger.warning(f"Failed to parse {resource_name} amount")
    
    def _on_detection_completed(self, event_data: Dict[str, Any]) -> None:
        """
        Handle detection completed events.
        
        Args:
            event_data: Event data
        """
        # Process detection results based on strategy
        strategy = event_data.get('strategy')
        results = event_data.get('results', [])
        
        if not results:
            return
            
        if strategy == 'template':
            self._process_template_results(results)
        elif strategy == 'ocr':
            self._process_ocr_results(results)
        elif strategy == 'yolo':
            self._process_yolo_results(results)
    
    def _process_template_results(self, results: List[Dict[str, Any]]) -> None:
        """
        Process template matching results.
        
        Args:
            results: Template matching results
        """
        # This would need to be customized based on what templates
        # correspond to what game elements
        for result in results:
            template_name = result.get('template_name', '')
            
            # Update game state based on detected templates
            # E.g., if we detected a city, resource node, etc.
            # This is just an example
            if 'city' in template_name:
                self._process_city_detection(result)
            elif 'resource' in template_name:
                self._process_resource_detection(result)
            # Add more template types as needed
    
    def _process_ocr_results(self, results: List[Dict[str, Any]]) -> None:
        """
        Process OCR results.
        
        Args:
            results: OCR results
        """
        # Process OCR results to update game state
        # This would depend on what text we're looking for
        pass
    
    def _process_yolo_results(self, results: List[Dict[str, Any]]) -> None:
        """
        Process YOLO detection results.
        
        Args:
            results: YOLO detection results
        """
        # Process YOLO results to update game state
        # This would depend on what objects we've trained the model to detect
        pass
    
    def _process_city_detection(self, detection: Dict[str, Any]) -> None:
        """
        Process city detection to update game state.
        
        Args:
            detection: City detection data
        """
        # Extract data from detection
        # This is a simplified example
        x = detection.get('x', 0)
        y = detection.get('y', 0)
        
        # We would need to translate screen coordinates to game coordinates
        if self._game_state.current_position:
            # This logic would depend on how the game UI maps screen position to game position
            # For now, we'll use a placeholder
            game_coords = self._screen_to_game_coords(x, y)
            
            if game_coords:
                # Create a map entity for the city
                entity = MapEntity(
                    entity_type='city',
                    coordinates=game_coords,
                    last_seen=datetime.now()
                )
                
                # Add to game state
                self._game_state.add_or_update_entity(entity)
                logger.debug(f"Added city at {game_coords}")
    
    def _process_resource_detection(self, detection: Dict[str, Any]) -> None:
        """
        Process resource node detection to update game state.
        
        Args:
            detection: Resource node detection data
        """
        # Similar to city detection, but for resource nodes
        # This would be customized based on game specifics
        pass
    
    def _screen_to_game_coords(self, screen_x: int, screen_y: int) -> Optional[Coordinates]:
        """
        Convert screen coordinates to game world coordinates.
        
        This is a placeholder - the actual conversion would depend on
        how the game maps screen position to world position.
        
        Args:
            screen_x: X coordinate on screen
            screen_y: Y coordinate on screen
            
        Returns:
            Coordinates in game world, or None if conversion not possible
        """
        # We need a current position to use as reference
        if not self._game_state.current_position:
            return None
            
        # This logic would need to be customized based on the game's UI
        # For now, just return the current position as a placeholder
        return self._game_state.current_position
    
    def _save_state(self) -> None:
        """Save game state to disk."""
        try:
            # We need to convert the state to a serializable format
            serialized = self._serialize_state()
            
            with open(self._state_file_path, 'w') as f:
                json.dump(serialized, f, indent=2)
                
            logger.debug(f"Saved game state to {self._state_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save game state: {e}")
    
    def _load_state(self) -> None:
        """Load game state from disk."""
        if not os.path.exists(self._state_file_path):
            logger.debug(f"No saved state found at {self._state_file_path}")
            return
            
        try:
            with open(self._state_file_path, 'r') as f:
                serialized = json.load(f)
                
            self._deserialize_state(serialized)
            logger.debug(f"Loaded game state from {self._state_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to load game state: {e}")
    
    def _serialize_state(self) -> Dict[str, Any]:
        """
        Convert game state to serializable dictionary.
        
        Returns:
            Dictionary representation of game state
        """
        # This is a simplified serialization - a complete implementation
        # would handle all aspects of the game state
        result = {
            'player': {
                'name': self._game_state.player_name,
                'level': self._game_state.player_level,
                'power': self._game_state.player_power
            },
            'current_position': None,
            'resources': {},
            'buildings': [],
            'armies': [],
            'known_entities': [],
            'explored_coordinates': [],
            'last_updated': self._game_state.last_updated.isoformat()
        }
        
        # Serialize current position
        if self._game_state.current_position:
            result['current_position'] = {
                'kingdom': self._game_state.current_position.kingdom,
                'x': self._game_state.current_position.x,
                'y': self._game_state.current_position.y
            }
            
        # Serialize resources
        for name, resource in self._game_state.resources.as_dict().items():
            result['resources'][name] = {
                'amount': resource.amount,
                'capacity': resource.capacity
            }
            
        # Serialize buildings
        for name, building in self._game_state.buildings.items():
            b_data = {
                'name': building.name,
                'level': building.level,
                'coordinates': None,
                'construction_time': None
            }
            
            if building.coordinates:
                b_data['coordinates'] = {
                    'kingdom': building.coordinates.kingdom,
                    'x': building.coordinates.x,
                    'y': building.coordinates.y
                }
                
            if building.construction_time:
                b_data['construction_time'] = building.construction_time.isoformat()
                
            result['buildings'].append(b_data)
            
        # Serialize known entities
        for entity in self._game_state.known_entities.values():
            e_data = {
                'entity_type': entity.entity_type,
                'coordinates': {
                    'kingdom': entity.coordinates.kingdom,
                    'x': entity.coordinates.x,
                    'y': entity.coordinates.y
                },
                'level': entity.level,
                'owner': entity.owner,
                'last_seen': entity.last_seen.isoformat(),
                'strength': entity.strength,
                'details': entity.details
            }
            
            result['known_entities'].append(e_data)
            
        # Serialize explored coordinates
        for coords in self._game_state.explored_coordinates:
            result['explored_coordinates'].append({
                'kingdom': coords.kingdom,
                'x': coords.x,
                'y': coords.y
            })
            
        return result
    
    def _deserialize_state(self, data: Dict[str, Any]) -> None:
        """
        Update game state from serialized dictionary.
        
        Args:
            data: Serialized game state
        """
        # This is a simplified deserialization - a complete implementation
        # would handle all aspects of the game state
        try:
            # Deserialize player info
            if 'player' in data:
                self._game_state.player_name = data['player'].get('name')
                self._game_state.player_level = data['player'].get('level')
                self._game_state.player_power = data['player'].get('power')
            
            # Deserialize current position
            if 'current_position' in data and data['current_position']:
                pos = data['current_position']
                self._game_state.current_position = Coordinates(
                    pos['kingdom'], pos['x'], pos['y']
                )
                
            # Deserialize resources
            if 'resources' in data:
                for name, res_data in data['resources'].items():
                    self._game_state.resources.update(
                        name, 
                        res_data.get('amount', 0), 
                        res_data.get('capacity')
                    )
                    
            # Deserialize buildings
            if 'buildings' in data:
                for b_data in data['buildings']:
                    building = Building(
                        name=b_data.get('name', ''),
                        level=b_data.get('level', 1)
                    )
                    
                    if 'coordinates' in b_data and b_data['coordinates']:
                        coords = b_data['coordinates']
                        building.coordinates = Coordinates(
                            coords['kingdom'], coords['x'], coords['y']
                        )
                        
                    if 'construction_time' in b_data and b_data['construction_time']:
                        building.construction_time = datetime.fromisoformat(
                            b_data['construction_time']
                        )
                        
                    self._game_state.buildings[building.name] = building
                    
            # Deserialize known entities
            if 'known_entities' in data:
                for e_data in data['known_entities']:
                    coords = e_data['coordinates']
                    coordinates = Coordinates(
                        coords['kingdom'], coords['x'], coords['y']
                    )
                    
                    entity = MapEntity(
                        entity_type=e_data.get('entity_type', ''),
                        coordinates=coordinates,
                        level=e_data.get('level'),
                        owner=e_data.get('owner'),
                        strength=e_data.get('strength'),
                        details=e_data.get('details', {})
                    )
                    
                    if 'last_seen' in e_data:
                        entity.last_seen = datetime.fromisoformat(e_data['last_seen'])
                        
                    self._game_state.add_or_update_entity(entity)
                    
            # Deserialize explored coordinates
            if 'explored_coordinates' in data:
                for coords_data in data['explored_coordinates']:
                    coords = Coordinates(
                        coords_data['kingdom'], 
                        coords_data['x'], 
                        coords_data['y']
                    )
                    self._game_state.explored_coordinates.add(coords)
                    
            # Deserialize last updated
            if 'last_updated' in data:
                self._game_state.last_updated = datetime.fromisoformat(data['last_updated'])
                
        except Exception as e:
            logger.error(f"Error deserializing game state: {e}")
    
    def _publish_state_changed_event(self) -> None:
        """Publish game state changed event."""
        if not self._event_bus:
            return
            
        # Create event data - only include basic information to avoid
        # sending too much data in events
        event_data = {
            'current_position': str(self._game_state.current_position) if self._game_state.current_position else None,
            'resources': {
                name: resource.amount 
                for name, resource in self._game_state.resources.as_dict().items()
            },
            'last_updated': self._game_state.last_updated.isoformat()
        }
        
        # Create and publish event
        event = Event(EventType.GAME_STATE_CHANGED, event_data)
        self._event_bus.publish(event)
        logger.debug("Published game state changed event") 