from typing import Optional, Dict, Any, List, Tuple
import logging
from PyQt6.QtCore import QObject, QPoint, QRect
from .window_tracker import WindowTracker

logger = logging.getLogger(__name__)

class CoordinateSpace:
    """Available coordinate spaces."""
    SCREEN = "SCREEN"    # Global screen coordinates
    WINDOW = "WINDOW"    # Relative to window
    CLIENT = "CLIENT"    # Relative to client area
    LOGICAL = "LOGICAL"  # DPI-independent
    PHYSICAL = "PHYSICAL"  # Raw physical pixels

class CoordinateManager(QObject):
    """
    Manages coordinate transformations and regions.
    
    This class provides:
    - Coordinate space transformations
    - Region tracking and management
    - DPI scaling handling
    - Coordinate validation
    """
    
    def __init__(self, window_tracker: WindowTracker) -> None:
        """
        Initialize coordinate manager.
        
        Args:
            window_tracker: Window tracker instance
        """
        super().__init__()
        
        self.window_tracker = window_tracker
        self.regions: Dict[str, Dict[str, Any]] = {}
        self.active_spaces = [
            CoordinateSpace.SCREEN,
            CoordinateSpace.WINDOW,
            CoordinateSpace.CLIENT
        ]
        
        # Connect to window tracker signals
        self.window_tracker.window_found.connect(self.on_window_found)
        self.window_tracker.window_lost.connect(self.on_window_lost)
        self.window_tracker.window_moved.connect(self.on_window_moved)
        
        logger.debug("Coordinate manager initialized")
        
    def transform_point(
        self,
        point: QPoint,
        from_space: str,
        to_space: str
    ) -> QPoint:
        """
        Transform point between coordinate spaces.
        
        Args:
            point: Point to transform
            from_space: Source coordinate space
            to_space: Target coordinate space
            
        Returns:
            Transformed point
            
        Raises:
            RuntimeError: If window geometry is not available
            ValueError: If coordinate space is invalid
        """
        try:
            # Validate coordinate spaces
            valid_spaces = [
                CoordinateSpace.SCREEN,
                CoordinateSpace.WINDOW,
                CoordinateSpace.CLIENT,
                CoordinateSpace.LOGICAL
            ]
            if from_space not in valid_spaces:
                raise ValueError(f"Invalid coordinate space: {from_space}")
            if to_space not in valid_spaces:
                raise ValueError(f"Invalid coordinate space: {to_space}")
            
            # Get window geometry
            window_rect = self.window_tracker.get_window_rect()
            client_rect = self.window_tracker.get_client_rect()
            
            if not window_rect or not client_rect:
                raise RuntimeError("Window geometry not available")
            
            # Calculate offsets
            window_offset = QPoint(window_rect.x(), window_rect.y())
            client_offset = QPoint(
                client_rect.x() - window_rect.x(),
                client_rect.y() - window_rect.y()
            )
            
            # Special case for window <-> client conversion
            if from_space == CoordinateSpace.WINDOW and to_space == CoordinateSpace.CLIENT:
                # Window point is relative to window origin
                # Client point should be relative to client origin
                # Subtract the client area offset from window coordinates
                return QPoint(
                    point.x() - client_offset.x(),
                    point.y() - client_offset.y()
                )
            elif from_space == CoordinateSpace.CLIENT and to_space == CoordinateSpace.WINDOW:
                # Client point is relative to client origin
                # Window point should be relative to window origin
                # Add the client area offset to client coordinates
                return QPoint(
                    point.x() + client_offset.x(),
                    point.y() + client_offset.y()
                )
            
            # Transform to screen space first
            screen_point = point
            if from_space == CoordinateSpace.WINDOW:
                screen_point = point + window_offset
            elif from_space == CoordinateSpace.CLIENT:
                screen_point = point + window_offset + client_offset
            elif from_space == CoordinateSpace.LOGICAL:
                physical = self.window_tracker.to_physical_pos(
                    (point.x(), point.y())
                )
                screen_point = QPoint(physical[0], physical[1])
            
            # Then transform to target space
            if to_space == CoordinateSpace.SCREEN:
                return screen_point
            elif to_space == CoordinateSpace.WINDOW:
                return screen_point - window_offset
            elif to_space == CoordinateSpace.CLIENT:
                return screen_point - window_offset - client_offset
            elif to_space == CoordinateSpace.LOGICAL:
                logical = self.window_tracker.to_logical_pos(
                    (screen_point.x(), screen_point.y())
                )
                return QPoint(logical[0], logical[1])
                
        except Exception as e:
            logger.error(f"Error transforming point: {e}")
            raise RuntimeError(f"Error transforming point: {e}")
            
    def add_region(
        self,
        name: str,
        rect: QRect,
        space: str = CoordinateSpace.SCREEN
    ) -> None:
        """
        Add tracked region.
        
        Args:
            name: Region identifier
            rect: Region rectangle
            space: Coordinate space of rectangle
            
        Raises:
            ValueError: If name is None or empty, or if space is invalid
        """
        try:
            # Validate inputs
            if name is None or not isinstance(name, str):
                logger.error("Region name must be a non-None string")
                return
                
            if not name.strip():
                logger.error("Region name cannot be empty")
                return
                
            valid_spaces = [
                CoordinateSpace.SCREEN,
                CoordinateSpace.WINDOW,
                CoordinateSpace.CLIENT,
                CoordinateSpace.LOGICAL
            ]
            if space not in valid_spaces:
                logger.error(f"Invalid coordinate space: {space}")
                return
                
            self.regions[name] = {
                "rect": rect,
                "space": space
            }
            logger.debug(f"Added region '{name}': {rect} ({space})")
            
        except Exception as e:
            logger.error(f"Error adding region: {e}")
            
    def remove_region(self, name: str) -> None:
        """
        Remove tracked region.
        
        Args:
            name: Region identifier
        """
        try:
            if name in self.regions:
                del self.regions[name]
                logger.debug(f"Removed region '{name}'")
                
        except Exception as e:
            logger.error(f"Error removing region: {e}")
            
    def get_region(
        self,
        name: str,
        space: str = CoordinateSpace.SCREEN
    ) -> QRect:
        """
        Get region in specified coordinate space.
        
        Args:
            name: Region identifier
            space: Target coordinate space
            
        Returns:
            Region rectangle in target space
            
        Raises:
            ValueError: If region does not exist
        """
        try:
            if name not in self.regions:
                raise ValueError(f"Region '{name}' not found")
                
            region = self.regions[name]
            rect = region["rect"]
            
            # Transform if needed
            if region["space"] != space:
                # Transform top-left corner
                top_left = self.transform_point(
                    QPoint(rect.left(), rect.top()),
                    region["space"],
                    space
                )
                
                # Keep original dimensions
                return QRect(
                    top_left.x(),
                    top_left.y(),
                    rect.width(),
                    rect.height()
                )
                
            return rect
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error getting region: {e}")
            raise ValueError(f"Error getting region: {e}")
            
    def is_valid_coordinate(self, point: QPoint, space: str) -> bool:
        """
        Check if coordinate is valid in specified space.
        
        Args:
            point: Point to check
            space: Coordinate space
            
        Returns:
            True if coordinate is valid
        """
        try:
            # Basic validation
            if point.x() < 0 or point.y() < 0:
                return False
                
            # Space-specific validation
            if space == CoordinateSpace.WINDOW:
                window_rect = self.window_tracker.get_window_rect()
                if not window_rect:
                    return False
                return (
                    point.x() < window_rect.width() and
                    point.y() < window_rect.height()
                )
                
            elif space == CoordinateSpace.CLIENT:
                client_rect = self.window_tracker.get_client_rect()
                if not client_rect:
                    return False
                return (
                    point.x() < client_rect.width() and
                    point.y() < client_rect.height()
                )
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating coordinate: {e}")
            return False
            
    def set_active_spaces(self, spaces: List[str]) -> None:
        """
        Set active coordinate spaces.
        
        Args:
            spaces: List of space identifiers
        """
        self.active_spaces = spaces
        logger.debug(f"Active spaces updated: {spaces}")
        
    def get_active_spaces(self) -> List[str]:
        """Get currently active coordinate spaces."""
        return self.active_spaces
        
    def on_window_found(self, hwnd: int) -> None:
        """Handle window found event."""
        logger.debug(f"Window found: {hwnd}")
        
    def on_window_lost(self) -> None:
        """Handle window lost event."""
        logger.debug("Window lost")
        
    def on_window_moved(self, rect: QRect) -> None:
        """Handle window moved event."""
        try:
            # Just log the move without string formatting to avoid recursion
            logger.debug("Window moved")
            
            # Update any regions that need to be transformed
            for name, region in self.regions.items():
                if region["space"] == CoordinateSpace.WINDOW:
                    # Transform region to new window position
                    self.get_region(name, CoordinateSpace.SCREEN)
                    
        except Exception as e:
            logger.error("Error handling window move", exc_info=True) 