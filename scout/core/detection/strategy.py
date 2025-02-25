"""
Detection Strategy

This module implements the Strategy pattern for detection algorithms.
It allows different detection algorithms to be used interchangeably
with the same interface.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np

class DetectionStrategy(ABC):
    """
    Base class for detection strategies.
    
    This implements the Strategy pattern, allowing different
    detection algorithms to be used interchangeably. Strategies:
    
    - Process images to find elements
    - Have consistent interfaces for configuration and execution
    - Can be swapped at runtime
    - Return standardized result formats
    """
    
    @abstractmethod
    def detect(self, image: np.ndarray, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Perform detection on an image.
        
        This method should be implemented by concrete strategy classes
        to perform the actual detection.
        
        Args:
            image: Image to analyze (OpenCV/numpy format)
            params: Detection parameters specific to the strategy
            
        Returns:
            List of detection results as dictionaries
            Each result should contain at minimum:
            - 'type': Type of detected element
            - 'x', 'y': Position coordinates
            - 'width', 'height': Dimensions
            - 'confidence': Detection confidence (0.0 to 1.0)
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of this detection strategy.
        
        Returns:
            Strategy name for identification
        """
        pass
    
    @abstractmethod
    def get_required_params(self) -> List[str]:
        """
        Get the required parameters for this strategy.
        
        Returns:
            List of parameter names that must be provided to detect()
        """
        pass 