"""
Search Patterns for 2D Grid Exploration

This module provides various search pattern generators for systematically exploring
a 2D grid space. These patterns can be used for automation sequences to search
for objects or resources in the game world.

Each pattern generator yields a sequence of (x, y) coordinates to visit.
"""

from typing import Generator, Tuple, List, Optional
import math


def spiral_pattern(
    center_x: int, 
    center_y: int, 
    max_radius: int, 
    step_size: int = 1
) -> Generator[Tuple[int, int], None, None]:
    """
    Generate coordinates in a spiral pattern starting from a center point.
    
    This pattern is efficient when targets are likely to be closer to the center.
    The spiral moves outward in a square pattern, visiting all points within the
    specified maximum radius.
    
    Args:
        center_x: X-coordinate of the center point
        center_y: Y-coordinate of the center point
        max_radius: Maximum distance from center to search (in grid units)
        step_size: Distance between consecutive points (default: 1)
        
    Yields:
        Tuples of (x, y) coordinates to visit
    """
    # Start at the center
    yield (center_x, center_y)
    
    # Spiral outward
    for radius in range(step_size, max_radius + 1, step_size):
        # Top edge (left to right)
        x = center_x - radius
        for i in range(0, 2 * radius + 1, step_size):
            yield (x + i, center_y - radius)
            
        # Right edge (top to bottom)
        y = center_y - radius
        for i in range(step_size, 2 * radius + 1, step_size):
            yield (center_x + radius, y + i)
            
        # Bottom edge (right to left)
        x = center_x + radius
        for i in range(step_size, 2 * radius + 1, step_size):
            yield (x - i, center_y + radius)
            
        # Left edge (bottom to top)
        y = center_y + radius
        for i in range(step_size, 2 * radius, step_size):
            yield (center_x - radius, y - i)


def grid_pattern(
    start_x: int, 
    start_y: int, 
    width: int, 
    height: int, 
    step_size: int = 1,
    snake: bool = True
) -> Generator[Tuple[int, int], None, None]:
    """
    Generate coordinates in a grid pattern, optionally in a snake-like pattern.
    
    This pattern systematically covers a rectangular area by moving in rows.
    The snake pattern alternates the direction of traversal for each row,
    which is more efficient for covering large areas.
    
    Args:
        start_x: X-coordinate of the starting corner
        start_y: Y-coordinate of the starting corner
        width: Width of the grid to search
        height: Height of the grid to search
        step_size: Distance between consecutive points (default: 1)
        snake: If True, alternate row direction (snake pattern)
              If False, always move left to right (raster pattern)
        
    Yields:
        Tuples of (x, y) coordinates to visit
    """
    for y in range(start_y, start_y + height, step_size):
        row_num = (y - start_y) // step_size
        
        # Determine if we should reverse this row (for snake pattern)
        reverse_row = snake and row_num % 2 == 1
        
        # Generate x coordinates for this row
        if reverse_row:
            x_range = range(start_x + width - step_size, start_x - 1, -step_size)
        else:
            x_range = range(start_x, start_x + width, step_size)
            
        # Yield each point in the row
        for x in x_range:
            yield (x, y)


def expanding_circles_pattern(
    center_x: int, 
    center_y: int, 
    max_radius: int, 
    step_size: int = 1,
    points_per_circle: int = 8
) -> Generator[Tuple[int, int], None, None]:
    """
    Generate coordinates in concentric circles around a center point.
    
    This pattern is useful when targets might be at a specific distance from
    the center, or when you want to prioritize checking in all directions
    at each distance increment.
    
    Args:
        center_x: X-coordinate of the center point
        center_y: Y-coordinate of the center point
        max_radius: Maximum distance from center to search (in grid units)
        step_size: Distance between consecutive circles (default: 1)
        points_per_circle: Minimum number of points to generate per circle
        
    Yields:
        Tuples of (x, y) coordinates to visit
    """
    # Start at the center
    yield (center_x, center_y)
    
    # Generate points in concentric circles
    for radius in range(step_size, max_radius + 1, step_size):
        # Calculate number of points needed for this circle
        # Scale with radius to maintain point density
        num_points = max(points_per_circle, int(2 * math.pi * radius))
        
        # Generate evenly spaced points around the circle
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = center_x + int(radius * math.cos(angle))
            y = center_y + int(radius * math.sin(angle))
            yield (x, y)


def quadtree_pattern(
    start_x: int, 
    start_y: int, 
    width: int, 
    height: int, 
    min_cell_size: int = 1
) -> Generator[Tuple[int, int], None, None]:
    """
    Generate coordinates using a quadtree-inspired approach.
    
    This pattern recursively divides the search space into quadrants,
    checking the center of each quadrant first before subdividing.
    It's efficient for quickly finding targets in a large area.
    
    Args:
        start_x: X-coordinate of the starting corner
        start_y: Y-coordinate of the starting corner
        width: Width of the area to search
        height: Height of the area to search
        min_cell_size: Minimum size of quadrant to check
        
    Yields:
        Tuples of (x, y) coordinates to visit
    """
    # Queue of regions to process: (x, y, width, height)
    queue = [(start_x, start_y, width, height)]
    
    while queue:
        x, y, w, h = queue.pop(0)
        
        # Check the center of this region
        center_x = x + w // 2
        center_y = y + h // 2
        yield (center_x, center_y)
        
        # If region is still larger than minimum size, subdivide
        if w > min_cell_size or h > min_cell_size:
            # Calculate new dimensions
            new_w = max(w // 2, min_cell_size)
            new_h = max(h // 2, min_cell_size)
            
            # Add the four quadrants to the queue
            # Top-left
            queue.append((x, y, new_w, new_h))
            # Top-right
            queue.append((x + new_w, y, w - new_w, new_h))
            # Bottom-left
            queue.append((x, y + new_h, new_w, h - new_h))
            # Bottom-right
            queue.append((x + new_w, y + new_h, w - new_w, h - new_h))


def create_search_sequence(
    pattern_name: str,
    positions: dict,
    **kwargs
) -> List[Tuple[int, int]]:
    """
    Create a sequence of coordinates using the specified pattern.
    
    This function converts a generator pattern into a list of coordinates
    that can be used to create an automation sequence.
    
    Args:
        pattern_name: Name of the pattern to use ('spiral', 'grid', 'circles', 'quadtree')
        positions: Dictionary of named positions that can be used as reference points
        **kwargs: Additional parameters for the specific pattern
        
    Returns:
        List of (x, y) coordinates to visit
    """
    # Get center position if specified
    center_pos = None
    if 'center_position' in kwargs and kwargs['center_position'] in positions:
        center_pos = positions[kwargs['center_position']]
        center_x = center_pos.x
        center_y = center_pos.y
    elif 'center_x' in kwargs and 'center_y' in kwargs:
        center_x = kwargs['center_x']
        center_y = kwargs['center_y']
    else:
        # Default to center of screen if no position specified
        center_x = 1920  # Assuming 1080p resolution
        center_y = 1080
    
    # Get start position for grid/quadtree patterns
    start_pos = None
    if 'start_position' in kwargs and kwargs['start_position'] in positions:
        start_pos = positions[kwargs['start_position']]
        start_x = start_pos.x
        start_y = start_pos.y
    elif 'start_x' in kwargs and 'start_y' in kwargs:
        start_x = kwargs['start_x']
        start_y = kwargs['start_y']
    else:
        # Default to top-left corner
        start_x = 0
        start_y = 0
    
    # Select the appropriate pattern generator
    if pattern_name == 'spiral':
        max_radius = kwargs.get('max_radius', 500)
        step_size = kwargs.get('step_size', 50)
        generator = spiral_pattern(center_x, center_y, max_radius, step_size)
    
    elif pattern_name == 'grid':
        width = kwargs.get('width', 1920)
        height = kwargs.get('height', 1080)
        step_size = kwargs.get('step_size', 50)
        snake = kwargs.get('snake', True)
        generator = grid_pattern(start_x, start_y, width, height, step_size, snake)
    
    elif pattern_name == 'circles':
        max_radius = kwargs.get('max_radius', 500)
        step_size = kwargs.get('step_size', 50)
        points_per_circle = kwargs.get('points_per_circle', 8)
        generator = expanding_circles_pattern(center_x, center_y, max_radius, step_size, points_per_circle)
    
    elif pattern_name == 'quadtree':
        width = kwargs.get('width', 1920)
        height = kwargs.get('height', 1080)
        min_cell_size = kwargs.get('min_cell_size', 50)
        generator = quadtree_pattern(start_x, start_y, width, height, min_cell_size)
    
    else:
        raise ValueError(f"Unknown pattern name: {pattern_name}")
    
    # Convert generator to list
    return list(generator) 