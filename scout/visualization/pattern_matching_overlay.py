"""Pattern matching overlay visualization."""

from typing import Optional, List, Tuple, Dict
import logging
import cv2
import numpy as np
from dataclasses import dataclass
from collections import defaultdict
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPaintEvent

from ..core import WindowTracker
from ..config import ConfigManager, PatternMatchingOverlayConfig
from ..capture import PatternMatcher, MatchResult

logger = logging.getLogger(__name__)

@dataclass
class GroupedMatch:
    """Represents a group of similar matches."""
    template_name: str
    confidence: float  # Average confidence
    rect: QRect       # Merged rectangle
    count: int        # Number of matches in group
    matches: List[MatchResult]  # Original matches

class PatternMatchingOverlay(QWidget):
    """
    Transparent overlay window for displaying pattern matches.
    
    This class provides:
    - Real-time visualization of pattern matches
    - Transparent window that syncs with game window
    - Customizable visual elements (rectangles, crosshairs, labels)
    - Click-through functionality
    - DPI scaling support
    
    The overlay is completely independent from:
    - OCR functionality
    - Region selection
    - Debug visualization
    """
    
    # Constants
    MAX_MATCHES = 100  # Maximum matches to store
    GROUP_DISTANCE_THRESHOLD = 50  # Pixels
    
    # Signals
    error_occurred = pyqtSignal(str)  # Error message
    
    def __init__(
        self,
        window_tracker: WindowTracker,
        pattern_matcher: PatternMatcher,
        config: ConfigManager,
        parent: Optional[QWidget] = None
    ) -> None:
        """Initialize pattern matching overlay."""
        super().__init__(parent)
        
        # Store components
        self.window_tracker = window_tracker
        self.pattern_matcher = pattern_matcher
        self.config = config
        
        # Initialize state
        self.settings = config.get_pattern_matching_overlay_config()
        self.current_matches: List[MatchResult] = []
        self.grouped_matches: List[GroupedMatch] = []
        self.is_active = False
        self._last_dpi_scale = 1.0
        
        # Setup window flags for transparent overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |  # No window frame
            Qt.WindowType.Tool |                 # No taskbar entry
            Qt.WindowType.WindowStaysOnTopHint | # Always on top
            Qt.WindowType.WindowTransparentForInput  # Click-through
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # Transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)  # Don't steal focus
        
        # Create update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_matches)
        
        # Connect signals
        self._connect_signals()
        
        logger.debug("Pattern matching overlay initialized")
    
    def _connect_signals(self) -> None:
        """Connect component signals."""
        # Window tracker signals
        self.window_tracker.window_found.connect(self._on_window_found)
        self.window_tracker.window_lost.connect(self._on_window_lost)
        self.window_tracker.window_moved.connect(self._on_window_moved)
        
        # Pattern matcher signals
        self.pattern_matcher.match_found.connect(self._on_match_found)
        self.pattern_matcher.match_failed.connect(self._on_match_failed)
    
    def start(self) -> None:
        """Start overlay visualization."""
        if not self.is_active:
            logger.info("Starting pattern matching overlay")
            self.is_active = True
            self._update_timer_interval()
            self.update_timer.start()
            self.show()
            self.raise_()  # Ensure window is on top
            logger.debug(f"Pattern matching overlay started and shown at geometry: {self.geometry()}")
    
    def stop(self) -> None:
        """Stop overlay visualization."""
        if self.is_active:
            logger.info("Stopping pattern matching overlay")
            self.is_active = False
            self.update_timer.stop()
            self.hide()
            self.current_matches.clear()
            self.grouped_matches.clear()
            logger.debug("Pattern matching overlay stopped and hidden")
    
    def _update_timer_interval(self) -> None:
        """Update timer interval from settings."""
        interval = int(1000 / self.settings.update_rate)  # Convert fps to ms
        self.update_timer.setInterval(interval)
        logger.debug(f"Update interval set to {interval}ms")
    
    def _group_matches(self) -> List[GroupedMatch]:
        """Group similar matches together.
        
        Groups matches that are close to each other and have the same template.
        Returns a list of grouped matches with averaged positions and confidences.
        """
        if not self.current_matches:
            return []
            
        # Sort matches by confidence (highest first)
        sorted_matches = sorted(
            self.current_matches,
            key=lambda m: m.confidence,
            reverse=True
        )
        
        # Group by template name first
        template_groups: Dict[str, List[MatchResult]] = defaultdict(list)
        for match in sorted_matches[:self.MAX_MATCHES]:  # Limit total matches
            template_groups[match.template_name].append(match)
        
        grouped_matches: List[GroupedMatch] = []
        
        for template_name, matches in template_groups.items():
            # Find groups within template matches
            while matches:
                base_match = matches[0]
                group = [base_match]
                remaining = []
                
                # Find all matches close to base match
                for other in matches[1:]:
                    if self._should_group(base_match, other):
                        group.append(other)
                    else:
                        remaining.append(other)
                
                # Create grouped match
                grouped_matches.append(self._create_group(group))
                matches = remaining
        
        return grouped_matches
    
    def _should_group(self, match1: MatchResult, match2: MatchResult) -> bool:
        """Determine if two matches should be grouped."""
        # Check distance between centers
        center1 = match1.rect.center()
        center2 = match2.rect.center()
        distance = ((center1.x() - center2.x()) ** 2 + 
                   (center1.y() - center2.y()) ** 2) ** 0.5
        return distance <= self.GROUP_DISTANCE_THRESHOLD
    
    def _create_group(self, matches: List[MatchResult]) -> GroupedMatch:
        """Create a grouped match from a list of matches."""
        if not matches:
            raise ValueError("Cannot create group from empty matches")
            
        # Calculate average confidence
        avg_confidence = sum(m.confidence for m in matches) / len(matches)
        
        # Calculate merged rectangle
        rects = [m.rect for m in matches]
        left = min(r.left() for r in rects)
        top = min(r.top() for r in rects)
        right = max(r.right() for r in rects)
        bottom = max(r.bottom() for r in rects)
        merged_rect = QRect(left, top, right - left, bottom - top)
        
        return GroupedMatch(
            template_name=matches[0].template_name,
            confidence=avg_confidence,
            rect=merged_rect,
            count=len(matches),
            matches=matches
        )
    
    def _update_matches(self) -> None:
        """Update pattern matches."""
        try:
            if not self.window_tracker.is_window_found():
                logger.debug("Window not found, skipping match update")
                return
                
            # Get current DPI scale
            dpi_scale = getattr(self.window_tracker, 'dpi_scale', 1.0)
            if dpi_scale != self._last_dpi_scale:
                logger.debug(f"DPI scale changed from {self._last_dpi_scale} to {dpi_scale}")
                self._last_dpi_scale = dpi_scale
                self._update_geometry()
            
            # Find and group matches
            logger.debug("Finding matches...")
            matches = self.pattern_matcher.find_matches()
            if matches:
                logger.info(f"Found {len(matches)} matches")
                self.current_matches = matches
                self.grouped_matches = self._group_matches()
                logger.debug(f"Grouped into {len(self.grouped_matches)} groups")
                self.update()  # Trigger repaint
            else:
                logger.debug("No matches found in update cycle")
                
        except Exception as e:
            logger.error(f"Error updating matches: {e}")
            self.error_occurred.emit(str(e))
    
    def _update_geometry(self) -> None:
        """Update overlay geometry to match client area."""
        try:
            # Get client rect
            client_rect = self.window_tracker.get_client_rect()
            if not client_rect:
                logger.warning("Could not get client rect")
                return
                
            # Set overlay geometry to match client area exactly
            self.setGeometry(client_rect)
            self.show()
            self.raise_()
            
            logger.debug(f"Updated overlay geometry to: {client_rect}")
            
        except Exception as e:
            logger.error(f"Error updating geometry: {e}")
            self.error_occurred.emit(str(e))
    
    def _on_window_found(self, hwnd: int) -> None:
        """Handle window found event."""
        try:
            logger.info(f"Window found event received: {hwnd}")
            # Get window geometry
            rect = self.window_tracker.get_client_rect()
            if rect:
                # Update overlay position and size
                logger.debug(f"Setting overlay geometry to: {rect}")
                self.setGeometry(rect)
                self.show()
                self.raise_()
                logger.info(f"Overlay shown and raised at: {self.geometry()}")
                
                # Force an immediate update
                self._update_matches()
            else:
                logger.warning("Window found but could not get client rect")
        except Exception as e:
            logger.error(f"Error handling window found: {e}")
            self.error_occurred.emit(str(e))
    
    def _on_window_lost(self) -> None:
        """Handle window lost event."""
        logger.info("Window lost event received")
        self.hide()
        self.current_matches.clear()
        self.grouped_matches.clear()
        logger.debug("Overlay hidden and matches cleared")
    
    def _on_window_moved(self, rect: QRect) -> None:
        """Handle window moved event."""
        try:
            logger.debug("Window moved, updating geometry")
            self._update_geometry()
        except Exception as e:
            logger.error(f"Error handling window move: {e}")
            self.error_occurred.emit(str(e))
    
    def _on_match_found(self, template: str, confidence: float, position: QPoint) -> None:
        """Handle match found event."""
        # Individual match events are not used, we get all matches in _update_matches
        pass
    
    def _on_match_failed(self, template: str, error: str) -> None:
        """Handle match failed event."""
        logger.warning(f"Match failed for {template}: {error}")
    
    def update_settings(self, settings: PatternMatchingOverlayConfig) -> None:
        """Update overlay settings.
        
        Args:
            settings: New settings to apply
        """
        self.settings = settings
        self._update_timer_interval()
        self.update()  # Trigger repaint
        logger.debug("Overlay settings updated")
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw pattern matches on the overlay.
        
        This method handles:
        - Drawing rectangles around matches
        - Drawing crosshairs at match centers
        - Drawing labels with match info
        - Proper coordinate transformation from screen to overlay space
        """
        try:
            # Get client rect for coordinate transformation
            client_rect = self.window_tracker.get_client_rect()
            if not client_rect:
                logger.warning("Could not get client rect for coordinate transformation")
                return
                
            # Create painter
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Make window transparent
            painter.fillRect(self.rect(), QColor(0, 0, 0, 1))
            
            # Draw all match groups
            for group in self._group_matches():
                self._draw_group(painter, group)
                
        except Exception as e:
            logger.error(f"Error in paintEvent: {e}")
            self.error_occurred.emit(str(e))
            
    def _draw_group(self, painter: QPainter, group: GroupedMatch) -> None:
        """Draw a group of matches.
        
        Args:
            painter: QPainter instance
            group: Group of matches to draw
        """
        try:
            # Get client rect for coordinate transformation
            client_rect = self.window_tracker.get_client_rect()
            if not client_rect:
                logger.warning("Could not get client rect for coordinate transformation")
                return
                
            # Get screen rect for offset calculation
            screen_rect = group.rect
            
            # Transform to overlay coordinates by subtracting client rect position
            # This works because the overlay is positioned exactly at the client rect
            overlay_rect = QRect(
                screen_rect.x() - client_rect.x(),
                screen_rect.y() - client_rect.y(),
                screen_rect.width(),
                screen_rect.height()
            )
            
            # Scale rect based on settings
            scaled_rect = self.settings.scale_match_rect(overlay_rect)
            
            logger.debug(
                f"Drawing match: screen={screen_rect}, "
                f"client={client_rect}, "
                f"overlay={overlay_rect}, "
                f"scaled={scaled_rect}"
            )
            
            # Draw rectangle
            self._draw_rectangle(painter, scaled_rect)
            
            # Draw crosshair at center
            center = scaled_rect.center()
            self._draw_crosshair(painter, center)
            
            # Draw label
            self._draw_group_label(painter, scaled_rect, group)
            
        except Exception as e:
            logger.error(f"Error drawing match group: {e}")
            self.error_occurred.emit(f"Error drawing match group: {e}")
            
    def _draw_rectangle(self, painter: QPainter, rect: QRect) -> None:
        """Draw rectangle with current settings.
        
        Args:
            painter: QPainter instance
            rect: Rectangle to draw
        """
        color = self._bgr_to_rgb(self.settings.rect_color)
        pen = QPen(QColor(*color))
        pen.setWidth(self.settings.rect_thickness)
        painter.setPen(pen)
        painter.drawRect(rect)
        
    def _draw_crosshair(self, painter: QPainter, center: QPoint) -> None:
        """Draw crosshair with current settings.
        
        Args:
            painter: QPainter instance
            center: Center point to draw at
        """
        color = self._bgr_to_rgb(self.settings.crosshair_color)
        pen = QPen(QColor(*color))
        pen.setWidth(self.settings.crosshair_thickness)
        painter.setPen(pen)
        
        size = self.settings.crosshair_size
        half_size = size // 2
        
        # Draw horizontal line
        painter.drawLine(
            center.x() - half_size,
            center.y(),
            center.x() + half_size,
            center.y()
        )
        
        # Draw vertical line
        painter.drawLine(
            center.x(),
            center.y() - half_size,
            center.x(),
            center.y() + half_size
        )
        
    def _draw_group_label(self, painter: QPainter, rect: QRect, group: GroupedMatch) -> None:
        """Draw label for match group.
        
        Args:
            painter: QPainter instance
            rect: Rectangle the label is for
            group: Match group to label
        """
        # Format label text
        label = self.settings.label_format.format(
            name=group.template_name,
            conf=group.confidence,
            count=group.count
        )
        
        # Set label style
        color = self._bgr_to_rgb(self.settings.label_color)
        pen = QPen(QColor(*color))
        pen.setWidth(self.settings.label_thickness)
        painter.setPen(pen)
        
        # Calculate font size based on rect height
        font = painter.font()
        font.setPointSizeF(self.settings.label_size * rect.height() / 100)
        painter.setFont(font)
        
        # Draw above rectangle
        painter.drawText(
            rect.left(),
            rect.top() - font.pointSize(),
            label
        )
    
    @staticmethod
    def _bgr_to_rgb(bgr: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Convert BGR color to RGB.
        
        Args:
            bgr: BGR color tuple
            
        Returns:
            RGB color tuple
        """
        return (bgr[2], bgr[1], bgr[0]) 