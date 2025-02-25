"""
Game State

This module provides data models for representing the state of the Total Battle game.
It defines structures for tracking game coordinates, resources, buildings, and other
game-specific information.
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class Coordinates:
    """
    Represents coordinates in the game world.
    
    In Total Battle, coordinates consist of:
    - kingdom (k): Which world the coordinates are in
    - x: Horizontal position (0-999)
    - y: Vertical position (0-999)
    """
    kingdom: int
    x: int
    y: int
    
    def __str__(self) -> str:
        """String representation of coordinates (K:X:Y format)."""
        return f"K:{self.kingdom} X:{self.x} Y:{self.y}"
    
    def __hash__(self) -> int:
        """Hash function for using coordinates as dictionary keys."""
        return hash((self.kingdom, self.x, self.y))
    
    def __eq__(self, other) -> bool:
        """Equality comparison for coordinates."""
        if not isinstance(other, Coordinates):
            return False
        return (self.kingdom == other.kingdom and 
                self.x == other.x and 
                self.y == other.y)
    
    def distance_to(self, other: 'Coordinates') -> Optional[int]:
        """
        Calculate Manhattan distance to another coordinate.
        
        Returns None if coordinates are in different kingdoms.
        """
        if self.kingdom != other.kingdom:
            return None
        return abs(self.x - other.x) + abs(self.y - other.y)

@dataclass
class Resource:
    """Represents a game resource with name, amount, and capacity."""
    name: str
    amount: int = 0
    capacity: Optional[int] = None
    
    def is_full(self) -> bool:
        """Check if resource is at capacity."""
        if self.capacity is None:
            return False
        return self.amount >= self.capacity

@dataclass
class Resources:
    """Collection of game resources."""
    gold: Resource = field(default_factory=lambda: Resource("Gold"))
    food: Resource = field(default_factory=lambda: Resource("Food"))
    wood: Resource = field(default_factory=lambda: Resource("Wood"))
    stone: Resource = field(default_factory=lambda: Resource("Stone"))
    iron: Resource = field(default_factory=lambda: Resource("Iron"))
    crystal: Resource = field(default_factory=lambda: Resource("Crystal"))
    
    def as_dict(self) -> Dict[str, Resource]:
        """Convert resources to dictionary."""
        return {
            "gold": self.gold,
            "food": self.food,
            "wood": self.wood,
            "stone": self.stone,
            "iron": self.iron,
            "crystal": self.crystal
        }
    
    def update(self, resource_name: str, amount: int, capacity: Optional[int] = None) -> None:
        """
        Update a resource amount and optionally capacity.
        
        Args:
            resource_name: Name of resource to update
            amount: New amount of resource
            capacity: New capacity (if applicable)
        """
        resource_map = self.as_dict()
        resource_name = resource_name.lower()
        
        if resource_name in resource_map:
            resource = resource_map[resource_name]
            resource.amount = amount
            if capacity is not None:
                resource.capacity = capacity
        else:
            logger.warning(f"Unknown resource: {resource_name}")

@dataclass
class Building:
    """Represents a building in the game."""
    name: str
    level: int = 1
    coordinates: Optional[Coordinates] = None
    construction_time: Optional[datetime] = None
    
    def is_upgrading(self) -> bool:
        """Check if building is currently being upgraded."""
        if self.construction_time is None:
            return False
        return self.construction_time > datetime.now()
    
    def time_remaining(self) -> Optional[int]:
        """Get seconds remaining for construction, or None if not upgrading."""
        if not self.is_upgrading():
            return None
        delta = self.construction_time - datetime.now()
        return max(0, int(delta.total_seconds()))

@dataclass
class Army:
    """Represents an army in the game."""
    name: str
    units: Dict[str, int] = field(default_factory=dict)
    coordinates: Optional[Coordinates] = None
    marching_to: Optional[Coordinates] = None
    arrival_time: Optional[datetime] = None
    
    def is_marching(self) -> bool:
        """Check if army is currently marching."""
        if self.arrival_time is None or self.marching_to is None:
            return False
        return self.arrival_time > datetime.now()
    
    def time_remaining(self) -> Optional[int]:
        """Get seconds remaining for march, or None if not marching."""
        if not self.is_marching():
            return None
        delta = self.arrival_time - datetime.now()
        return max(0, int(delta.total_seconds()))
    
    def total_units(self) -> int:
        """Get total number of units in army."""
        return sum(self.units.values())

@dataclass
class MapEntity:
    """
    Represents an entity on the game map (city, resource node, monster, etc).
    
    This is used to track scouted map objects that have been identified
    by the detection system.
    """
    entity_type: str  # city, resource, monster, boss, ruins, etc.
    coordinates: Coordinates
    level: Optional[int] = None
    owner: Optional[str] = None
    last_seen: datetime = field(default_factory=datetime.now)
    strength: Optional[int] = None
    details: Dict[str, any] = field(default_factory=dict)

@dataclass
class GameState:
    """
    Central data structure for tracking game state.
    
    This class maintains:
    - Current player position and view
    - Resources
    - Buildings
    - Armies
    - Known map entities
    """
    # Player information
    player_name: Optional[str] = None
    player_level: Optional[int] = None
    player_power: Optional[int] = None
    current_position: Optional[Coordinates] = None
    
    # Resources, buildings, armies
    resources: Resources = field(default_factory=Resources)
    buildings: Dict[str, Building] = field(default_factory=dict)
    armies: Dict[str, Army] = field(default_factory=dict)
    
    # Map knowledge
    known_entities: Dict[Coordinates, MapEntity] = field(default_factory=dict)
    explored_coordinates: Set[Coordinates] = field(default_factory=set)
    
    # Game status
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update_timestamp(self) -> None:
        """Update the last updated timestamp."""
        self.last_updated = datetime.now()
    
    def add_or_update_entity(self, entity: MapEntity) -> None:
        """
        Add or update a map entity.
        
        Args:
            entity: MapEntity to add or update
        """
        self.known_entities[entity.coordinates] = entity
        self.explored_coordinates.add(entity.coordinates)
        
    def get_entities_by_type(self, entity_type: str) -> List[MapEntity]:
        """
        Get all known entities of a specific type.
        
        Args:
            entity_type: Type of entities to return
            
        Returns:
            List of map entities matching the specified type
        """
        return [
            entity for entity in self.known_entities.values()
            if entity.entity_type == entity_type
        ]

    def get_entities_by_owner(self, owner: str) -> List[MapEntity]:
        """
        Get all known entities belonging to a specific owner.
        
        Args:
            owner: Owner name
            
        Returns:
            List of map entities belonging to the specified owner
        """
        return [
            entity for entity in self.known_entities.values()
            if entity.owner == owner
        ]
    
    def get_nearest_entity(self, 
                        coordinates: Coordinates, 
                        entity_type: Optional[str] = None) -> Optional[Tuple[MapEntity, int]]:
        """
        Find the nearest entity to the given coordinates, optionally filtered by type.
        
        Args:
            coordinates: Reference coordinates
            entity_type: Optional entity type filter
            
        Returns:
            Tuple of (entity, distance) or None if no matching entity found
        """
        if not self.known_entities:
            return None
            
        candidates = self.known_entities.values()
        if entity_type:
            candidates = [e for e in candidates if e.entity_type == entity_type]
            
        if not candidates:
            return None
            
        nearest = None
        min_distance = float('inf')
        
        for entity in candidates:
            if entity.coordinates.kingdom != coordinates.kingdom:
                continue
                
            distance = coordinates.distance_to(entity.coordinates)
            if distance < min_distance:
                min_distance = distance
                nearest = entity
                
        if nearest is None:
            return None
            
        return (nearest, min_distance) 