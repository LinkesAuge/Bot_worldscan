"""
Search Automation Utilities

This module provides utilities for creating automation sequences that follow
search patterns. It integrates the search pattern generators with the automation
system to create sequences that systematically explore areas in the game.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path
import json

from scout.automation.core import AutomationPosition, AutomationSequence, AutomationManager
from scout.automation.actions import AutomationAction, ActionType, ClickParams
from scout.automation.search_patterns import create_search_sequence

logger = logging.getLogger(__name__)


class SearchPatternAutomation:
    """
    Utility class for creating automation sequences that follow search patterns.
    
    This class integrates the search pattern generators with the automation system
    to create sequences that systematically explore areas in the game.
    """
    
    def __init__(self, automation_manager: AutomationManager):
        """
        Initialize the search pattern automation utility.
        
        Args:
            automation_manager: The automation manager instance
        """
        self.automation_manager = automation_manager
        
    def create_search_sequence(
        self,
        name: str,
        pattern_name: str,
        action_type: ActionType = ActionType.CLICK,
        **kwargs
    ) -> AutomationSequence:
        """
        Create an automation sequence that follows a search pattern.
        
        Args:
            name: Name for the new sequence
            pattern_name: Type of search pattern ('spiral', 'grid', 'circles', 'quadtree')
            action_type: Type of action to perform at each point (default: CLICK)
            **kwargs: Additional parameters for the search pattern
            
        Returns:
            An AutomationSequence object that can be executed
        """
        # Get the list of coordinates from the pattern generator
        coordinates = create_search_sequence(
            pattern_name, 
            self.automation_manager.positions,
            **kwargs
        )
        
        # Create temporary positions for each coordinate
        temp_positions = {}
        actions = []
        
        for i, (x, y) in enumerate(coordinates):
            # Create a temporary position
            pos_name = f"temp_search_pos_{i}"
            temp_pos = AutomationPosition(pos_name, x, y)
            temp_positions[pos_name] = temp_pos
            
            # Create an action for this position
            if action_type == ActionType.CLICK:
                params = ClickParams(
                    position_name=pos_name,
                    description=f"Search point {i+1}/{len(coordinates)}"
                )
                action = AutomationAction(action_type, params)
                actions.append(action.to_dict())
        
        # Create the sequence
        sequence = AutomationSequence(
            name=name,
            actions=actions,
            description=f"Search pattern: {pattern_name} with {len(coordinates)} points"
        )
        
        return sequence
    
    def save_search_sequence(self, sequence: AutomationSequence) -> None:
        """
        Save a search sequence to disk.
        
        Args:
            sequence: The sequence to save
        """
        self.automation_manager.add_sequence(sequence)
        logger.info(f"Saved search sequence: {sequence.name}")
    
    def create_and_save_search_sequence(
        self,
        name: str,
        pattern_name: str,
        action_type: ActionType = ActionType.CLICK,
        **kwargs
    ) -> AutomationSequence:
        """
        Create and save a search sequence in one step.
        
        Args:
            name: Name for the new sequence
            pattern_name: Type of search pattern ('spiral', 'grid', 'circles', 'quadtree')
            action_type: Type of action to perform at each point (default: CLICK)
            **kwargs: Additional parameters for the search pattern
            
        Returns:
            The created and saved AutomationSequence
        """
        sequence = self.create_search_sequence(name, pattern_name, action_type, **kwargs)
        self.save_search_sequence(sequence)
        return sequence
    
    def visualize_pattern(
        self,
        pattern_name: str,
        output_path: str = "search_pattern_visualization.json",
        **kwargs
    ) -> None:
        """
        Create a visualization of a search pattern and save it to a JSON file.
        
        This is useful for debugging and visualizing search patterns before
        creating automation sequences.
        
        Args:
            pattern_name: Type of search pattern ('spiral', 'grid', 'circles', 'quadtree')
            output_path: Path to save the visualization JSON file
            **kwargs: Additional parameters for the search pattern
        """
        # Get the list of coordinates from the pattern generator
        coordinates = create_search_sequence(
            pattern_name, 
            self.automation_manager.positions,
            **kwargs
        )
        
        # Create a list of points with indices
        points = [{"index": i, "x": x, "y": y} for i, (x, y) in enumerate(coordinates)]
        
        # Save to JSON file
        with open(output_path, 'w') as f:
            json.dump({
                "pattern": pattern_name,
                "parameters": kwargs,
                "points": points
            }, f, indent=2)
            
        logger.info(f"Saved pattern visualization to {output_path}")
        
    def get_pattern_description(self, pattern_name: str) -> str:
        """
        Get a description of a search pattern.
        
        Args:
            pattern_name: Name of the pattern ('spiral', 'grid', 'circles', 'quadtree')
            
        Returns:
            A string describing the pattern and its characteristics
        """
        descriptions = {
            "spiral": (
                "Spiral Pattern: Starts at the center and moves outward in a spiral. "
                "Efficient when targets are likely to be closer to the center."
            ),
            "grid": (
                "Grid Pattern: Systematically covers a rectangular area by moving in rows. "
                "The snake pattern alternates row direction for efficiency."
            ),
            "circles": (
                "Expanding Circles Pattern: Generates points in concentric circles around a center. "
                "Useful when targets might be at a specific distance from the center."
            ),
            "quadtree": (
                "Quadtree Pattern: Recursively divides the search space into quadrants. "
                "Efficient for quickly finding targets in a large area."
            )
        }
        
        return descriptions.get(pattern_name, f"Unknown pattern: {pattern_name}") 