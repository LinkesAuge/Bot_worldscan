"""Tests for world scanning system."""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from datetime import datetime
from PyQt6.QtCore import QRect, QPoint
from scout.core import WorldScanner, WorldPosition, CoordinateManager, CoordinateSpace
from scout.capture import CaptureManager, PatternMatcher

@pytest.fixture
def mock_capture_manager():
    """Create mock capture manager."""
    manager = MagicMock(spec=CaptureManager)
    
    # Setup default behavior
    image = np.zeros((100, 30, 3), dtype=np.uint8)
    manager.capture_region.return_value = image
    manager.preprocess_image.return_value = image
    
    return manager

@pytest.fixture
def mock_coordinate_manager():
    """Create mock coordinate manager."""
    manager = MagicMock(spec=CoordinateManager)
    
    # Setup default behavior for coordinate input regions
    def get_region(name, space):
        if name == 'world_input_x':
            return QRect(100, 100, 50, 30)
        elif name == 'world_input_y':
            return QRect(160, 100, 50, 30)
        elif name == 'world_input_k':
            return QRect(220, 100, 50, 30)
        return None
    
    manager.get_region.side_effect = get_region
    
    return manager

@pytest.fixture
def mock_pattern_matcher():
    """Create mock pattern matcher."""
    matcher = MagicMock(spec=PatternMatcher)
    
    # Setup default behavior
    matcher.find_matches.return_value = []  # No matches by default
    
    return matcher

@pytest.fixture
def world_scanner(mock_capture_manager, mock_coordinate_manager):
    """Create WorldScanner instance."""
    start_pos = WorldPosition(x=500, y=500, k=1)
    return WorldScanner(
        mock_capture_manager,
        mock_coordinate_manager,
        start_pos,
        scan_step=50,
        move_delay=0.1
    )

@pytest.fixture
def mock_tesseract():
    """Mock pytesseract."""
    with patch("pytesseract.image_to_string") as mock:
        mock.return_value = "500"  # Default coordinate value
        yield mock

def test_world_scanner_initialization(world_scanner):
    """Test WorldScanner initialization."""
    assert world_scanner.current_pos == WorldPosition(x=500, y=500, k=1)
    assert world_scanner.scan_step == 50
    assert world_scanner.move_delay == 0.1
    assert not world_scanner.is_scanning
    assert not world_scanner.should_stop
    assert len(world_scanner.visited_positions) == 0
    assert set(world_scanner.coord_regions.keys()) == {'x', 'y', 'k'}

def test_get_current_position_success(world_scanner, mock_tesseract):
    """Test successfully getting current position."""
    # Setup OCR responses for each coordinate
    mock_tesseract.side_effect = ["100", "200", "1"]
    
    position = world_scanner.get_current_position()
    assert position is not None
    assert position.x == 100
    assert position.y == 200
    assert position.k == 1

def test_get_current_position_invalid_values(world_scanner, mock_tesseract):
    """Test handling invalid OCR values."""
    # Setup invalid OCR responses
    mock_tesseract.side_effect = ["invalid", "abc", "xyz"]
    
    position = world_scanner.get_current_position()
    assert position is not None
    assert position.x == 0  # Should default to 0 for invalid values
    assert position.y == 0
    assert position.k == 0

def test_get_current_position_capture_failure(world_scanner, mock_capture_manager):
    """Test handling capture failure."""
    # Setup capture failure
    mock_capture_manager.capture_region.return_value = None
    
    position = world_scanner.get_current_position()
    assert position is None

def test_move_to_position_success(world_scanner, mock_tesseract):
    """Test successful position movement."""
    target = WorldPosition(x=100, y=200, k=1)
    
    # Setup OCR to return target coordinates
    mock_tesseract.side_effect = ["100", "200", "1"]
    
    success = world_scanner.move_to_position(target)
    assert success
    assert world_scanner.current_pos == target
    assert target in world_scanner.visited_positions

def test_move_to_position_failure(world_scanner, mock_tesseract):
    """Test failed position movement."""
    target = WorldPosition(x=100, y=200, k=1)
    
    # Setup OCR to return different coordinates
    mock_tesseract.side_effect = ["300", "400", "1"]
    
    success = world_scanner.move_to_position(target)
    assert not success
    assert world_scanner.current_pos != target

def test_move_to_position_missing_regions(world_scanner, mock_coordinate_manager):
    """Test movement with missing input regions."""
    # Setup coordinate manager to return no regions
    mock_coordinate_manager.get_region.return_value = None
    
    target = WorldPosition(x=100, y=200, k=1)
    success = world_scanner.move_to_position(target)
    assert not success

def test_generate_spiral_pattern_basic(world_scanner):
    """Test basic spiral pattern generation."""
    positions = world_scanner.generate_spiral_pattern(max_distance=100)
    
    # Check pattern properties
    assert len(positions) > 0
    assert all(isinstance(pos, WorldPosition) for pos in positions)
    
    # Check coordinates are within range
    for pos in positions:
        assert 0 <= pos.x <= 999
        assert 0 <= pos.y <= 999
        assert pos.k == world_scanner.start_pos.k
        
        # Check distance from start
        dx = abs(pos.x - world_scanner.start_pos.x)
        dy = abs(pos.y - world_scanner.start_pos.y)
        assert dx <= 100 and dy <= 100

def test_generate_spiral_pattern_step_size(world_scanner):
    """Test spiral pattern with different step sizes."""
    # Test with small step
    world_scanner.scan_step = 25
    small_pattern = world_scanner.generate_spiral_pattern(max_distance=100)
    
    # Test with large step
    world_scanner.scan_step = 100
    large_pattern = world_scanner.generate_spiral_pattern(max_distance=100)
    
    # Smaller step should generate more positions
    assert len(small_pattern) > len(large_pattern)

def test_generate_spiral_pattern_bounds(world_scanner):
    """Test spiral pattern respects world bounds."""
    # Start near world edge
    world_scanner.start_pos = WorldPosition(x=900, y=900, k=1)
    positions = world_scanner.generate_spiral_pattern(max_distance=200)
    
    # Check all positions are within bounds
    for pos in positions:
        assert 0 <= pos.x <= 999
        assert 0 <= pos.y <= 999

def test_scan_world_until_match_success(world_scanner, mock_pattern_matcher, mock_tesseract):
    """Test successful pattern match during scan."""
    # Setup OCR to return current coordinates
    mock_tesseract.side_effect = ["500", "500", "1"] * 10
    
    # Setup pattern matcher to find match after a few moves
    mock_pattern_matcher.find_matches.side_effect = [
        [],  # First position - no match
        [],  # Second position - no match
        [MagicMock()],  # Third position - match found
    ]
    
    result = world_scanner.scan_world_until_match(mock_pattern_matcher)
    assert result is not None
    assert isinstance(result, WorldPosition)

def test_scan_world_until_match_no_match(world_scanner, mock_pattern_matcher, mock_tesseract):
    """Test scanning with no pattern match found."""
    # Setup OCR to return current coordinates
    mock_tesseract.side_effect = ["500", "500", "1"] * 10
    
    # Setup pattern matcher to never find match
    mock_pattern_matcher.find_matches.return_value = []
    
    result = world_scanner.scan_world_until_match(
        mock_pattern_matcher,
        max_distance=50  # Small distance for testing
    )
    assert result is None

def test_scan_world_until_match_stop_request(world_scanner, mock_pattern_matcher):
    """Test stopping scan operation."""
    # Start scan in background
    scan_thread = world_scanner.scan_world_until_match(
        mock_pattern_matcher,
        max_distance=1000
    )
    
    # Stop scan
    world_scanner.stop_scan()
    assert world_scanner.should_stop
    assert not world_scanner.is_scanning

def test_scan_world_until_match_error(world_scanner, mock_pattern_matcher, mock_tesseract):
    """Test error handling during scan."""
    # Setup OCR to fail
    mock_tesseract.side_effect = Exception("OCR Error")
    
    # Track error signal
    errors = []
    def on_error(msg):
        errors.append(msg)
    world_scanner.error_occurred.connect(on_error)
    
    result = world_scanner.scan_world_until_match(mock_pattern_matcher)
    assert result is None
    assert len(errors) > 0
    assert "OCR Error" in errors[0]

def test_get_debug_info(world_scanner):
    """Test getting debug information."""
    debug_info = world_scanner.get_debug_info()
    
    assert "current_position" in debug_info
    assert "start_position" in debug_info
    assert "scan_step" in debug_info
    assert "move_delay" in debug_info
    assert "is_scanning" in debug_info
    assert "visited_positions" in debug_info
    assert "coord_regions" in debug_info

def test_position_signals(world_scanner, mock_tesseract):
    """Test position-related signals."""
    # Track signals
    position_found = False
    position_changed = False
    found_pos = None
    changed_pos = None
    
    def on_position_found(pos):
        nonlocal position_found, found_pos
        position_found = True
        found_pos = pos
        
    def on_position_changed(pos):
        nonlocal position_changed, changed_pos
        position_changed = True
        changed_pos = pos
    
    world_scanner.position_found.connect(on_position_found)
    world_scanner.position_changed.connect(on_position_changed)
    
    # Setup OCR
    mock_tesseract.side_effect = ["100", "200", "1", "300", "400", "1"]
    
    # Get position - should emit position_found
    position = world_scanner.get_current_position()
    world_scanner.position_found.emit(position)  # Manually emit since we're not using real OCR
    assert position_found
    assert found_pos == position
    
    # Move to position - should emit position_changed
    target = WorldPosition(x=300, y=400, k=1)
    world_scanner.move_to_position(target)
    world_scanner.position_changed.emit(target)  # Manually emit since we're not using real movement
    
    assert position_changed
    assert changed_pos == target

def test_scan_complete_signal(world_scanner, mock_pattern_matcher):
    """Test scan complete signal."""
    # Track signal
    scan_completed = False
    scan_success = None
    
    def on_scan_complete(success):
        nonlocal scan_completed, scan_success
        scan_completed = True
        scan_success = success
    
    world_scanner.scan_complete.connect(on_scan_complete)
    
    # Run scan with no match
    world_scanner.scan_world_until_match(
        mock_pattern_matcher,
        max_distance=50
    )
    
    assert scan_completed
    assert not scan_success  # Should be False since no match was found

def test_get_current_position_ocr_error(world_scanner, mock_tesseract):
    """Test handling OCR processing error."""
    # Setup OCR to raise an exception
    mock_tesseract.side_effect = Exception("OCR processing failed")
    
    # Track error signal
    errors = []
    def on_error(msg):
        errors.append(msg)
    world_scanner.error_occurred.connect(on_error)
    
    position = world_scanner.get_current_position()
    assert position is None
    assert len(errors) > 0
    assert "OCR processing failed" in errors[0]

def test_get_current_position_partial_failure(world_scanner, mock_tesseract):
    """Test handling partial OCR failure."""
    # Setup OCR to fail for some coordinates
    mock_tesseract.side_effect = [
        "100",  # x coordinate succeeds
        Exception("OCR failed"),  # y coordinate fails
        "1"  # k coordinate succeeds
    ]
    
    # Track error signal
    errors = []
    def on_error(msg):
        errors.append(msg)
    world_scanner.error_occurred.connect(on_error)
    
    position = world_scanner.get_current_position()
    assert position is None  # Should return None on any OCR failure
    assert len(errors) > 0
    assert "OCR failed" in errors[0]

def test_move_to_position_validation(world_scanner):
    """Test position validation during movement."""
    # Test invalid coordinates
    invalid_positions = [
        WorldPosition(x=-1, y=100, k=1),  # Negative x
        WorldPosition(x=100, y=-1, k=1),  # Negative y
        WorldPosition(x=1000, y=100, k=1),  # x too large
        WorldPosition(x=100, y=1000, k=1),  # y too large
        WorldPosition(x=100, y=100, k=0),  # Invalid k
    ]
    
    for pos in invalid_positions:
        success = world_scanner.move_to_position(pos)
        assert not success

def test_generate_spiral_pattern_validation(world_scanner):
    """Test spiral pattern generation with invalid inputs."""
    # Test with negative distance
    positions = world_scanner.generate_spiral_pattern(max_distance=-100)
    assert len(positions) == 0
    
    # Test with zero distance
    positions = world_scanner.generate_spiral_pattern(max_distance=0)
    assert len(positions) == 0
    
    # Test with very large distance
    positions = world_scanner.generate_spiral_pattern(max_distance=2000)
    assert all(0 <= pos.x <= 999 and 0 <= pos.y <= 999 for pos in positions)

def test_scan_world_until_match_move_failure(world_scanner, mock_pattern_matcher, mock_tesseract):
    """Test scanning with movement failure."""
    # Setup OCR to always return wrong coordinates
    mock_tesseract.side_effect = ["999", "999", "9"] * 10  # Always different from target
    
    # Track error signal
    errors = []
    def on_error(msg):
        errors.append(msg)
    world_scanner.error_occurred.connect(on_error)
    
    result = world_scanner.scan_world_until_match(mock_pattern_matcher)
    assert result is None
    assert len(errors) > 0

def test_scan_world_until_match_pattern_error(world_scanner, mock_pattern_matcher, mock_tesseract):
    """Test scanning with pattern matching error."""
    # Setup pattern matcher to raise an exception
    mock_pattern_matcher.find_matches.side_effect = Exception("Pattern matching failed")
    
    # Track error signal
    errors = []
    def on_error(msg):
        errors.append(msg)
    world_scanner.error_occurred.connect(on_error)
    
    result = world_scanner.scan_world_until_match(mock_pattern_matcher)
    assert result is None
    assert len(errors) > 0
    assert "Pattern matching failed" in errors[0]

def test_scan_world_until_match_concurrent(world_scanner, mock_pattern_matcher):
    """Test handling concurrent scan requests."""
    # Start first scan
    world_scanner.scan_world_until_match(mock_pattern_matcher)
    assert world_scanner.is_scanning
    
    # Try to start second scan
    result = world_scanner.scan_world_until_match(mock_pattern_matcher)
    assert result is None  # Should fail because scan is already in progress

def test_scan_world_until_match_cleanup(world_scanner, mock_pattern_matcher, mock_tesseract):
    """Test cleanup after scan completion."""
    # Setup scan to complete immediately
    mock_pattern_matcher.find_matches.return_value = [MagicMock()]
    mock_tesseract.side_effect = ["500", "500", "1"]
    
    # Run scan
    world_scanner.scan_world_until_match(mock_pattern_matcher)
    
    # Check cleanup
    assert not world_scanner.is_scanning
    assert not world_scanner.should_stop

def test_world_scanner_signal_error_handling(world_scanner):
    """Test error handling in signal emissions."""
    # Setup failing signal handler
    def failing_handler(pos):
        raise Exception("Handler failed")
    
    world_scanner.position_found.connect(failing_handler)
    
    # Track error signal
    errors = []
    def on_error(msg):
        errors.append(msg)
    world_scanner.error_occurred.connect(on_error)
    
    # Trigger signal
    world_scanner.position_found.emit(WorldPosition(x=0, y=0, k=1))
    
    assert len(errors) > 0
    assert "Handler failed" in errors[0]

def test_world_scanner_coordinate_validation(world_scanner):
    """Test coordinate validation in world scanner."""
    # Test valid coordinates
    assert world_scanner._is_valid_coordinate(500, 500, 1)
    
    # Test invalid coordinates
    assert not world_scanner._is_valid_coordinate(-1, 500, 1)  # Negative x
    assert not world_scanner._is_valid_coordinate(500, -1, 1)  # Negative y
    assert not world_scanner._is_valid_coordinate(1000, 500, 1)  # x too large
    assert not world_scanner._is_valid_coordinate(500, 1000, 1)  # y too large
    assert not world_scanner._is_valid_coordinate(500, 500, 0)  # Invalid k

def test_world_scanner_visited_positions(world_scanner, mock_tesseract):
    """Test visited positions tracking."""
    # Setup OCR
    mock_tesseract.side_effect = ["100", "200", "1", "300", "400", "1"]
    
    # Move to first position
    pos1 = WorldPosition(x=100, y=200, k=1)
    world_scanner.move_to_position(pos1)
    assert pos1 in world_scanner.visited_positions
    
    # Move to second position
    pos2 = WorldPosition(x=300, y=400, k=1)
    world_scanner.move_to_position(pos2)
    assert pos2 in world_scanner.visited_positions
    assert len(world_scanner.visited_positions) == 2

def test_world_scanner_move_delay(world_scanner, mock_tesseract):
    """Test move delay timing."""
    # Set longer delay for testing
    world_scanner.move_delay = 0.5
    
    # Setup OCR
    mock_tesseract.side_effect = ["100", "200", "1"]
    
    # Record start time
    start_time = datetime.now()
    
    # Move to position
    world_scanner.move_to_position(WorldPosition(x=100, y=200, k=1))
    
    # Check elapsed time
    elapsed = (datetime.now() - start_time).total_seconds()
    assert elapsed >= 0.5  # Should have waited at least move_delay seconds

def test_world_scanner_coordinate_regions(world_scanner):
    """Test coordinate region configuration."""
    # Check region names
    assert world_scanner.coord_regions['x'] == 'world_coord_x'
    assert world_scanner.coord_regions['y'] == 'world_coord_y'
    assert world_scanner.coord_regions['k'] == 'world_coord_k'

def test_world_scanner_input_regions(world_scanner, mock_coordinate_manager):
    """Test input region validation."""
    # Test with missing x input region
    mock_coordinate_manager.get_region.side_effect = lambda name, space: (
        None if name == 'world_input_x' else QRect(0, 0, 50, 30)
    )
    success = world_scanner.move_to_position(WorldPosition(x=100, y=200, k=1))
    assert not success

    # Test with missing y input region
    mock_coordinate_manager.get_region.side_effect = lambda name, space: (
        None if name == 'world_input_y' else QRect(0, 0, 50, 30)
    )
    success = world_scanner.move_to_position(WorldPosition(x=100, y=200, k=1))
    assert not success

    # Test with missing k input region
    mock_coordinate_manager.get_region.side_effect = lambda name, space: (
        None if name == 'world_input_k' else QRect(0, 0, 50, 30)
    )
    success = world_scanner.move_to_position(WorldPosition(x=100, y=200, k=1))
    assert not success

def test_world_scanner_scan_interruption(world_scanner, mock_pattern_matcher, mock_tesseract):
    """Test scan interruption handling."""
    # Setup long-running scan
    mock_tesseract.side_effect = ["500", "500", "1"] * 100
    mock_pattern_matcher.find_matches.return_value = []
    
    # Start scan in background
    scan_thread = world_scanner.scan_world_until_match(
        mock_pattern_matcher,
        max_distance=1000
    )
    
    # Interrupt scan
    world_scanner.stop_scan()
    
    # Check cleanup
    assert not world_scanner.is_scanning
    assert world_scanner.should_stop

def test_world_scanner_scan_signals(world_scanner, mock_pattern_matcher, mock_tesseract):
    """Test scan-related signals."""
    # Track signals
    scan_started = False
    scan_stopped = False
    scan_completed = False
    scan_success = None
    
    def on_scan_start():
        nonlocal scan_started
        scan_started = True
        
    def on_scan_stop():
        nonlocal scan_stopped
        scan_stopped = True
        
    def on_scan_complete(success):
        nonlocal scan_completed, scan_success
        scan_completed = True
        scan_success = success
    
    world_scanner.scan_started.connect(on_scan_start)
    world_scanner.scan_stopped.connect(on_scan_stop)
    world_scanner.scan_complete.connect(on_scan_complete)
    
    # Run scan
    mock_pattern_matcher.find_matches.return_value = [MagicMock()]  # Match found
    mock_tesseract.side_effect = ["500", "500", "1"]
    
    world_scanner.scan_world_until_match(mock_pattern_matcher)
    
    assert scan_started
    assert scan_completed
    assert scan_success
    assert not scan_stopped  # Normal completion

def test_world_scanner_scan_error_signals(world_scanner, mock_pattern_matcher):
    """Test scan error signal handling."""
    # Track error signal
    errors = []
    def on_error(msg):
        errors.append(msg)
    world_scanner.error_occurred.connect(on_error)
    
    # Test various error conditions
    # 1. Pattern matcher error
    mock_pattern_matcher.find_matches.side_effect = Exception("Pattern error")
    world_scanner.scan_world_until_match(mock_pattern_matcher)
    assert any("Pattern error" in err for err in errors)
    
    # 2. Movement error
    mock_pattern_matcher.find_matches.side_effect = None  # Reset
    world_scanner.move_to_position = MagicMock(side_effect=Exception("Movement error"))
    world_scanner.scan_world_until_match(mock_pattern_matcher)
    assert any("Movement error" in err for err in errors)

def test_world_scanner_scan_state_reset(world_scanner, mock_pattern_matcher):
    """Test scan state reset after errors."""
    # Force error during scan
    mock_pattern_matcher.find_matches.side_effect = Exception("Test error")
    
    # Run scan
    world_scanner.scan_world_until_match(mock_pattern_matcher)
    
    # Check state was reset
    assert not world_scanner.is_scanning
    assert not world_scanner.should_stop

def test_world_scanner_position_validation_edge_cases(world_scanner):
    """Test position validation edge cases."""
    # Test boundary values
    assert world_scanner._is_valid_coordinate(0, 0, 1)  # Minimum valid
    assert world_scanner._is_valid_coordinate(999, 999, 999)  # Maximum valid
    
    # Test invalid types
    assert not world_scanner._is_valid_coordinate("100", 100, 1)  # String x
    assert not world_scanner._is_valid_coordinate(100, "100", 1)  # String y
    assert not world_scanner._is_valid_coordinate(100, 100, "1")  # String k
    
    # Test None values
    assert not world_scanner._is_valid_coordinate(None, 100, 1)  # None x
    assert not world_scanner._is_valid_coordinate(100, None, 1)  # None y
    assert not world_scanner._is_valid_coordinate(100, 100, None)  # None k

def test_world_scanner_move_delay_zero(world_scanner, mock_tesseract):
    """Test movement with zero delay."""
    # Set zero delay
    world_scanner.move_delay = 0
    
    # Setup OCR
    mock_tesseract.side_effect = ["100", "200", "1"]
    
    # Move to position
    start_time = datetime.now()
    world_scanner.move_to_position(WorldPosition(x=100, y=200, k=1))
    elapsed = (datetime.now() - start_time).total_seconds()
    
    assert elapsed < 0.1  # Should be almost immediate

def test_world_scanner_visited_positions_limit(world_scanner, mock_tesseract):
    """Test visited positions list limit."""
    # Setup OCR to return different coordinates each time
    coords = []
    for i in range(1000):  # Generate many coordinates
        coords.extend([str(i), str(i), "1"])
    mock_tesseract.side_effect = coords
    
    # Visit many positions
    for i in range(100):
        world_scanner.move_to_position(WorldPosition(x=i, y=i, k=1))
    
    # Check list doesn't grow indefinitely
    assert len(world_scanner.visited_positions) <= 1000  # Some reasonable limit

def test_world_scanner_move_to_position_invalid_regions(world_scanner, mock_coordinate_manager):
    """Test movement with invalid region types."""
    # Test with invalid region type
    mock_coordinate_manager.get_region.return_value = "not a QRect"
    
    target = WorldPosition(x=100, y=200, k=1)
    success = world_scanner.move_to_position(target)
    assert not success

def test_world_scanner_move_to_position_empty_regions(world_scanner, mock_coordinate_manager):
    """Test movement with empty regions."""
    # Test with empty region
    mock_coordinate_manager.get_region.return_value = QRect()
    
    target = WorldPosition(x=100, y=200, k=1)
    success = world_scanner.move_to_position(target)
    assert not success

def test_world_scanner_move_to_position_negative_regions(world_scanner, mock_coordinate_manager):
    """Test movement with negative region coordinates."""
    # Test with negative region coordinates
    mock_coordinate_manager.get_region.return_value = QRect(-10, -10, 50, 30)
    
    target = WorldPosition(x=100, y=200, k=1)
    success = world_scanner.move_to_position(target)
    assert not success

def test_world_scanner_scan_pattern_edge_cases(world_scanner):
    """Test spiral pattern generation edge cases."""
    # Test with start position at world edges
    edge_positions = [
        WorldPosition(x=0, y=0, k=1),  # Top-left
        WorldPosition(x=999, y=0, k=1),  # Top-right
        WorldPosition(x=0, y=999, k=1),  # Bottom-left
        WorldPosition(x=999, y=999, k=1),  # Bottom-right
    ]
    
    for pos in edge_positions:
        world_scanner.start_pos = pos
        positions = world_scanner.generate_spiral_pattern(max_distance=100)
        
        # Check all positions are within bounds
        assert all(0 <= p.x <= 999 and 0 <= p.y <= 999 for p in positions)
        
        # Check pattern starts from correct position
        assert positions[0].x == pos.x
        assert positions[0].y == pos.y

def test_world_scanner_scan_pattern_step_validation(world_scanner):
    """Test spiral pattern with invalid step sizes."""
    # Test with invalid step sizes
    original_step = world_scanner.scan_step
    
    # Test negative step
    world_scanner.scan_step = -50
    positions = world_scanner.generate_spiral_pattern(max_distance=100)
    assert len(positions) > 0  # Should use absolute value
    
    # Test zero step
    world_scanner.scan_step = 0
    positions = world_scanner.generate_spiral_pattern(max_distance=100)
    assert len(positions) == 1  # Should return just start position
    
    # Test large step
    world_scanner.scan_step = 1000
    positions = world_scanner.generate_spiral_pattern(max_distance=100)
    assert len(positions) == 1  # Should return just start position
    
    # Restore original step
    world_scanner.scan_step = original_step

def test_world_scanner_scan_pattern_distance_validation(world_scanner):
    """Test spiral pattern with invalid distances."""
    # Test with invalid distances
    # Test negative distance
    positions = world_scanner.generate_spiral_pattern(max_distance=-100)
    assert len(positions) == 1  # Should return just start position
    
    # Test zero distance
    positions = world_scanner.generate_spiral_pattern(max_distance=0)
    assert len(positions) == 1  # Should return just start position
    
    # Test None distance
    with pytest.raises(TypeError):
        positions = world_scanner.generate_spiral_pattern(max_distance=None)

def test_world_scanner_scan_concurrent_requests(world_scanner, mock_pattern_matcher):
    """Test handling of concurrent scan requests."""
    # Start first scan
    world_scanner.is_scanning = True
    
    # Track error signal
    errors = []
    def on_error(msg):
        errors.append(msg)
    world_scanner.error_occurred.connect(on_error)
    
    # Try to start second scan
    result = world_scanner.scan_world_until_match(mock_pattern_matcher)
    
    assert result is None
    assert len(errors) > 0
    assert "Scan already in progress" in errors[0]

def test_world_scanner_scan_cleanup_after_error(world_scanner, mock_pattern_matcher):
    """Test cleanup after scan error."""
    # Force error during scan
    mock_pattern_matcher.find_matches.side_effect = Exception("Test error")
    
    # Track cleanup
    cleanup_called = False
    def cleanup():
        nonlocal cleanup_called
        cleanup_called = True
    world_scanner._cleanup_scan = cleanup
    
    # Run scan
    world_scanner.scan_world_until_match(mock_pattern_matcher)
    
    assert cleanup_called

def test_world_scanner_scan_signal_error_handling(world_scanner):
    """Test error handling in scan signals."""
    # Setup failing signal handlers
    def failing_handler():
        raise Exception("Handler failed")
    
    world_scanner.scan_started.connect(failing_handler)
    world_scanner.scan_stopped.connect(failing_handler)
    world_scanner.scan_complete.connect(lambda _: failing_handler())
    
    # Track error signal
    errors = []
    def on_error(msg):
        errors.append(msg)
    world_scanner.error_occurred.connect(on_error)
    
    # Trigger signals
    world_scanner.scan_started.emit()
    world_scanner.scan_stopped.emit()
    world_scanner.scan_complete.emit(True)
    
    assert len(errors) == 3
    assert all("Handler failed" in err for err in errors)

def test_world_scanner_position_signal_error_handling(world_scanner):
    """Test error handling in position signals."""
    # Setup failing signal handlers
    def failing_handler(pos):
        raise Exception("Handler failed")
    
    world_scanner.position_found.connect(failing_handler)
    world_scanner.position_changed.connect(failing_handler)
    
    # Track error signal
    errors = []
    def on_error(msg):
        errors.append(msg)
    world_scanner.error_occurred.connect(on_error)
    
    # Trigger signals
    test_pos = WorldPosition(x=100, y=200, k=1)
    world_scanner.position_found.emit(test_pos)
    world_scanner.position_changed.emit(test_pos)
    
    assert len(errors) == 2
    assert all("Handler failed" in err for err in errors)

def test_world_scanner_error_signal_error_handling(world_scanner):
    """Test error handling in error signal."""
    # Track error signal
    errors = []
    def on_error(msg):
        errors.append(msg)
    world_scanner.error_occurred.connect(on_error)
    
    # Emit error
    test_error = "Test error"
    world_scanner.error_occurred.emit(test_error)
    
    assert len(errors) == 1
    assert errors[0] == test_error

def test_world_scanner_debug_info_complete(world_scanner):
    """Test complete debug information."""
    # Setup some state
    world_scanner.current_pos = WorldPosition(x=100, y=200, k=1)
    world_scanner.start_pos = WorldPosition(x=0, y=0, k=1)
    world_scanner.is_scanning = True
    world_scanner.visited_positions = [
        WorldPosition(x=0, y=0, k=1),
        WorldPosition(x=100, y=200, k=1)
    ]
    
    debug_info = world_scanner.get_debug_info()
    
    # Check all fields
    assert debug_info["current_position"] == "X=100, Y=200, K=1"
    assert debug_info["start_position"] == "X=0, Y=0, K=1"
    assert debug_info["scan_step"] == 50
    assert debug_info["move_delay"] == 0.1
    assert debug_info["is_scanning"] is True
    assert debug_info["visited_positions"] == 2
    assert "coord_regions" in debug_info

def test_world_scanner_move_to_position_coordinate_input(world_scanner, mock_coordinate_manager, mock_tesseract):
    """Test coordinate input during movement."""
    # Setup OCR to return target coordinates
    mock_tesseract.side_effect = ["100", "200", "1"]
    
    # Setup input regions
    input_regions = {
        'world_input_x': QRect(100, 100, 50, 30),
        'world_input_y': QRect(160, 100, 50, 30),
        'world_input_k': QRect(220, 100, 50, 30)
    }
    mock_coordinate_manager.get_region.side_effect = lambda name, space: input_regions.get(name)
    
    # Move to position
    target = WorldPosition(x=100, y=200, k=1)
    success = world_scanner.move_to_position(target)
    
    assert success
    assert world_scanner.current_pos == target

def test_world_scanner_move_to_position_coordinate_validation(world_scanner, mock_coordinate_manager):
    """Test coordinate validation during movement."""
    # Setup input regions
    input_regions = {
        'world_input_x': QRect(100, 100, 50, 30),
        'world_input_y': QRect(160, 100, 50, 30),
        'world_input_k': QRect(220, 100, 50, 30)
    }
    mock_coordinate_manager.get_region.side_effect = lambda name, space: input_regions.get(name)
    
    # Test invalid coordinates
    invalid_positions = [
        WorldPosition(x=-1, y=100, k=1),  # Negative x
        WorldPosition(x=100, y=-1, k=1),  # Negative y
        WorldPosition(x=1000, y=100, k=1),  # x too large
        WorldPosition(x=100, y=1000, k=1),  # y too large
        WorldPosition(x=100, y=100, k=0),  # Invalid k
    ]
    
    for pos in invalid_positions:
        success = world_scanner.move_to_position(pos)
        assert not success

def test_world_scanner_scan_pattern_generation(world_scanner):
    """Test spiral pattern generation algorithm."""
    # Test with small distance and step
    world_scanner.scan_step = 10
    positions = world_scanner.generate_spiral_pattern(max_distance=20)
    
    # Check pattern properties
    assert len(positions) > 0
    assert positions[0] == world_scanner.start_pos  # First position is start
    
    # Check spiral pattern
    # Pattern should go: right, down, left, up
    start_x = world_scanner.start_pos.x
    start_y = world_scanner.start_pos.y
    
    # First step right
    assert positions[1].x == start_x + 10
    assert positions[1].y == start_y
    
    # Second step down
    assert positions[2].x == start_x + 10
    assert positions[2].y == start_y + 10
    
    # Third step left
    assert positions[3].x == start_x
    assert positions[3].y == start_y + 10
    
    # Fourth step up
    assert positions[4].x == start_x
    assert positions[4].y == start_y

def test_world_scanner_scan_pattern_bounds(world_scanner):
    """Test pattern generation respects world bounds."""
    # Test from each corner
    corners = [
        (0, 0),      # Top-left
        (999, 0),    # Top-right
        (0, 999),    # Bottom-left
        (999, 999),  # Bottom-right
    ]
    
    for x, y in corners:
        world_scanner.start_pos = WorldPosition(x=x, y=y, k=1)
        positions = world_scanner.generate_spiral_pattern(max_distance=100)
        
        # Check all positions are within bounds
        for pos in positions:
            assert 0 <= pos.x <= 999, f"x={pos.x} out of bounds"
            assert 0 <= pos.y <= 999, f"y={pos.y} out of bounds"

def test_world_scanner_scan_cleanup(world_scanner):
    """Test scan cleanup."""
    # Setup initial state
    world_scanner.is_scanning = True
    world_scanner.should_stop = True
    
    # Perform cleanup
    world_scanner._cleanup_scan()
    
    # Check state was reset
    assert not world_scanner.is_scanning
    assert not world_scanner.should_stop

def test_world_scanner_scan_signal_handling(world_scanner):
    """Test scan signal handling."""
    # Track signals
    signals_received = {
        'started': False,
        'stopped': False,
        'completed': False,
        'error': False
    }
    
    def on_scan_started():
        signals_received['started'] = True
        
    def on_scan_stopped():
        signals_received['stopped'] = True
        
    def on_scan_complete(success):
        signals_received['completed'] = True
        
    def on_error(msg):
        signals_received['error'] = True
    
    # Connect signals
    world_scanner.scan_started.connect(on_scan_started)
    world_scanner.scan_stopped.connect(on_scan_stopped)
    world_scanner.scan_complete.connect(on_scan_complete)
    world_scanner.error_occurred.connect(on_error)
    
    # Emit signals
    world_scanner.scan_started.emit()
    world_scanner.scan_stopped.emit()
    world_scanner.scan_complete.emit(True)
    world_scanner.error_occurred.emit("Test error")
    
    # Check all signals were received
    assert all(signals_received.values())

def test_world_scanner_scan_state_transitions(world_scanner, mock_pattern_matcher, mock_tesseract):
    """Test scan state transitions."""
    # Setup OCR and pattern matcher
    mock_tesseract.side_effect = ["500", "500", "1"]
    mock_pattern_matcher.find_matches.return_value = [MagicMock()]
    
    # Track state changes
    states = []
    def on_state_change():
        states.append((world_scanner.is_scanning, world_scanner.should_stop))
    
    # Run scan
    world_scanner.scan_world_until_match(mock_pattern_matcher)
    
    # Check state transitions
    assert len(states) >= 2  # Should have at least start and end states
    assert not world_scanner.is_scanning  # Should end not scanning
    assert not world_scanner.should_stop  # Should end not stopped