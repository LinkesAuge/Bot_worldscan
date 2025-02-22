"""Tests for pattern matching system."""

import pytest
import numpy as np
import cv2
from unittest.mock import MagicMock, patch
from pathlib import Path
from PyQt6.QtCore import QPoint, QRect
from scout.capture.pattern_matcher import PatternMatcher, MatchResult

@pytest.fixture
def mock_capture_manager():
    """Create mock capture manager."""
    manager = MagicMock()
    
    # Setup default behavior
    image = np.zeros((600, 800, 3), dtype=np.uint8)  # BGR image
    manager.capture_window.return_value = image
    manager.preprocess_image.return_value = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # Convert to grayscale for matching
    manager.dpi_scale = 1.5  # Set default DPI scale
    
    return manager

@pytest.fixture
def test_template():
    """Create test template for pattern matching tests."""
    # Create a simple template image (BGR)
    template = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(template, (25, 25), (75, 75), (255, 255, 255), -1)
    return cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)  # Convert to grayscale for matching

@pytest.fixture
def test_image():
    """Create test image for pattern matching."""
    # Create a larger image with the template pattern (BGR)
    image = np.zeros((600, 800, 3), dtype=np.uint8)
    cv2.rectangle(image, (100, 100), (150, 150), (255, 255, 255), -1)
    return image  # Pattern matcher will convert to grayscale

@pytest.fixture
def mock_cv2():
    """Mock OpenCV functions."""
    with patch("cv2.imread") as mock_imread, \
         patch("cv2.cvtColor") as mock_cvtColor, \
         patch("cv2.matchTemplate") as mock_match, \
         patch("cv2.minMaxLoc") as mock_minmax:
        
        # Setup default behavior
        mock_imread.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cvtColor.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_match.return_value = np.array([[0.96]])  # Single match result
        mock_minmax.return_value = (0.0, 0.96, (0, 0), (100, 100))  # min_val, max_val, min_loc, max_loc
        
        yield {
            "imread": mock_imread,
            "cvtColor": mock_cvtColor,
            "match": mock_match,
            "minmax": mock_minmax
        }

@pytest.fixture
def pattern_matcher(mock_capture_manager, tmp_path):
    """Create PatternMatcher instance with temporary directory."""
    # Create template directory
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    
    # Create test template
    template_path = template_dir / "test.png"
    cv2.imwrite(str(template_path), np.zeros((100, 100, 3), dtype=np.uint8))
    
    return PatternMatcher(mock_capture_manager, str(template_dir))

def test_pattern_matcher_initialization(pattern_matcher, tmp_path):
    """Test PatternMatcher initialization."""
    assert pattern_matcher.template_dir == tmp_path / "templates"
    assert pattern_matcher.confidence_threshold == 0.95
    assert isinstance(pattern_matcher.templates, dict)
    assert isinstance(pattern_matcher.template_sizes, dict)

def test_reload_templates_empty_dir(pattern_matcher, tmp_path):
    """Test reloading templates from empty directory."""
    # Clear template directory
    for file in pattern_matcher.template_dir.glob("*.png"):
        file.unlink()
    
    pattern_matcher.reload_templates()
    assert len(pattern_matcher.templates) == 0
    assert len(pattern_matcher.template_sizes) == 0

def test_reload_templates_with_invalid_files(pattern_matcher, tmp_path):
    """Test handling invalid template files."""
    # Create invalid template file
    invalid_file = pattern_matcher.template_dir / "invalid.png"
    invalid_file.write_text("not an image")
    
    # Should not raise exception
    pattern_matcher.reload_templates()
    assert "invalid" not in pattern_matcher.templates

def test_reload_templates_with_subdirectory(pattern_matcher, tmp_path):
    """Test loading templates from subdirectory."""
    # Create subdirectory with template
    subdir = pattern_matcher.template_dir / "subdir"
    subdir.mkdir()
    template_path = subdir / "subtest.png"
    cv2.imwrite(str(template_path), np.zeros((100, 100, 3), dtype=np.uint8))
    
    pattern_matcher.reload_templates("subdir")
    assert "subtest" in pattern_matcher.templates
    assert pattern_matcher.template_sizes["subtest"] == (100, 100)

def test_reload_templates_with_multiple_files(pattern_matcher, tmp_path):
    """Test loading multiple template files."""
    # Create multiple templates
    for i in range(3):
        template_path = pattern_matcher.template_dir / f"test{i}.png"
        cv2.imwrite(str(template_path), np.zeros((100, 100, 3), dtype=np.uint8))
    
    pattern_matcher.reload_templates()
    assert len(pattern_matcher.templates) == 4  # Including original test.png
    assert all(f"test{i}" in pattern_matcher.templates for i in range(3))

def test_reload_templates_clears_existing(pattern_matcher, tmp_path):
    """Test that reloading templates clears existing ones."""
    # Add a template
    template_path = pattern_matcher.template_dir / "new.png"
    cv2.imwrite(str(template_path), np.zeros((100, 100, 3), dtype=np.uint8))
    
    # Load initial templates
    pattern_matcher.reload_templates()
    initial_count = len(pattern_matcher.templates)
    
    # Remove template and reload
    template_path.unlink()
    pattern_matcher.reload_templates()
    
    assert len(pattern_matcher.templates) < initial_count
    assert "new" not in pattern_matcher.templates

def test_reload_templates_with_grayscale_conversion(pattern_matcher, mock_cv2):
    """Test template grayscale conversion."""
    pattern_matcher.reload_templates()
    
    # Verify color conversion was called
    mock_cv2["cvtColor"].assert_called_with(
        mock_cv2["imread"].return_value,
        cv2.COLOR_BGR2GRAY
    )

def test_reload_templates_with_none_image(pattern_matcher, mock_cv2):
    """Test handling None return from imread."""
    mock_cv2["imread"].return_value = None
    pattern_matcher.reload_templates()
    assert len(pattern_matcher.templates) == 0

def test_reload_templates_with_invalid_directory(pattern_matcher):
    """Test loading from non-existent directory."""
    pattern_matcher.template_dir = Path("nonexistent")
    pattern_matcher.reload_templates()
    assert len(pattern_matcher.templates) == 0

def test_non_max_suppression(pattern_matcher):
    """Test non-maxima suppression."""
    # Create overlapping matches
    matches = [
        MatchResult("test", 0.9, QPoint(100, 100), QRect(90, 90, 20, 20)),
        MatchResult("test", 0.8, QPoint(105, 105), QRect(95, 95, 20, 20)),  # Overlaps with first
        MatchResult("test", 0.7, QPoint(200, 200), QRect(190, 190, 20, 20))  # No overlap
    ]
    
    # Apply NMS
    filtered = pattern_matcher._non_max_suppression(matches)
    
    assert len(filtered) == 2
    assert filtered[0].confidence == 0.9  # Highest confidence match kept
    assert filtered[1].position == QPoint(200, 200)  # Non-overlapping match kept

def test_non_max_suppression_empty_input(pattern_matcher):
    """Test non-maxima suppression with empty input."""
    filtered = pattern_matcher._non_max_suppression([])
    assert filtered == []

def test_non_max_suppression_no_overlap(pattern_matcher):
    """Test non-maxima suppression with non-overlapping matches."""
    matches = [
        MatchResult("test", 0.9, QPoint(100, 100), QRect(90, 90, 20, 20)),
        MatchResult("test", 0.8, QPoint(200, 200), QRect(190, 190, 20, 20)),
        MatchResult("test", 0.7, QPoint(300, 300), QRect(290, 290, 20, 20))
    ]
    
    filtered = pattern_matcher._non_max_suppression(matches)
    assert len(filtered) == 3  # All matches kept
    assert [m.confidence for m in filtered] == [0.9, 0.8, 0.7]

def test_find_matches_single_template(pattern_matcher, mock_cv2, test_template, test_image):
    """Test finding matches for a single template."""
    # Setup template
    pattern_matcher.templates["test"] = test_template
    pattern_matcher.template_sizes["test"] = (100, 100)
    
    # Configure mock match results
    mock_cv2["match"].return_value = np.array([[0.96]])
    mock_cv2["minmax"].return_value = (0.0, 0.96, (0, 0), (100, 100))
    
    # Track match signal
    match_data = []
    def on_match(template, confidence, position):
        match_data.append((template, confidence, position))
    pattern_matcher.match_found.connect(on_match)
    
    # Find matches
    results = pattern_matcher.find_matches(["test"])
    
    assert len(results) == 1
    assert isinstance(results[0], MatchResult)
    assert results[0].template_name == "test"
    assert results[0].confidence == 0.96
    assert isinstance(results[0].position, QPoint)
    assert isinstance(results[0].rect, QRect)
    
    # Verify signal was emitted
    assert len(match_data) == 1
    assert match_data[0][0] == "test"
    assert match_data[0][1] == 0.96
    assert isinstance(match_data[0][2], QPoint)

def test_find_matches_multiple_templates(pattern_matcher, mock_cv2, test_template):
    """Test finding matches for multiple templates."""
    # Setup templates
    pattern_matcher.templates["test1"] = test_template
    pattern_matcher.templates["test2"] = test_template
    pattern_matcher.template_sizes["test1"] = (100, 100)
    pattern_matcher.template_sizes["test2"] = (100, 100)
    
    # Configure mock match results
    mock_cv2["match"].side_effect = [
        np.array([[0.97]]),  # First template
        np.array([[0.98]])   # Second template
    ]
    mock_cv2["minmax"].side_effect = [
        (0.0, 0.97, (0, 0), (100, 100)),
        (0.0, 0.98, (0, 0), (200, 200))
    ]
    
    # Find matches
    results = pattern_matcher.find_matches(["test1", "test2"])
    
    assert len(results) == 2
    assert results[0].template_name == "test1"
    assert results[0].confidence == 0.97
    assert results[1].template_name == "test2"
    assert results[1].confidence == 0.98

def test_find_matches_below_threshold(pattern_matcher, mock_cv2, test_template):
    """Test handling matches below confidence threshold."""
    # Setup template
    pattern_matcher.templates["test"] = test_template
    pattern_matcher.template_sizes["test"] = (100, 100)
    pattern_matcher.confidence_threshold = 0.95
    
    # Configure mock match results
    mock_cv2["match"].return_value = np.array([[0.94]])
    mock_cv2["minmax"].return_value = (0.0, 0.94, (0, 0), (100, 100))
    
    # Track failed match signal
    failed_data = []
    def on_failed(template, error):
        failed_data.append((template, error))
    pattern_matcher.match_failed.connect(on_failed)
    
    # Find matches
    results = pattern_matcher.find_matches(["test"])
    
    assert len(results) == 0
    assert len(failed_data) == 1
    assert failed_data[0][0] == "test"
    assert "confidence" in failed_data[0][1].lower()

def test_find_matches_invalid_template(pattern_matcher, mock_cv2):
    """Test handling invalid template name."""
    # Track failed match signal
    failed_data = []
    def on_failed(template, error):
        failed_data.append((template, error))
    pattern_matcher.match_failed.connect(on_failed)
    
    # Find matches for non-existent template
    results = pattern_matcher.find_matches(["nonexistent"])
    
    assert len(results) == 0
    assert len(failed_data) == 1
    assert failed_data[0][0] == "nonexistent"
    assert "not found" in failed_data[0][1].lower()

def test_find_matches_empty_image(pattern_matcher, mock_cv2, test_template):
    """Test handling empty capture image."""
    # Setup template
    pattern_matcher.templates["test"] = test_template
    pattern_matcher.template_sizes["test"] = (100, 100)
    
    # Make capture return None
    pattern_matcher.capture_manager.capture_window.return_value = None
    
    # Track failed match signal
    failed_data = []
    def on_failed(template, error):
        failed_data.append((template, error))
    pattern_matcher.match_failed.connect(on_failed)
    
    # Find matches
    results = pattern_matcher.find_matches(["test"])
    
    assert len(results) == 0
    assert len(failed_data) == 1
    assert failed_data[0][0] == "test"
    assert "capture failed" in failed_data[0][1].lower()

def test_find_matches_preprocessing_error(pattern_matcher, mock_cv2, test_template):
    """Test handling preprocessing error."""
    # Setup template
    pattern_matcher.templates["test"] = test_template
    pattern_matcher.template_sizes["test"] = (100, 100)
    
    # Make preprocessing raise error
    pattern_matcher.capture_manager.preprocess_image.side_effect = Exception("Preprocessing error")
    
    # Track failed match signal
    failed_data = []
    def on_failed(template, error):
        failed_data.append((template, error))
    pattern_matcher.match_failed.connect(on_failed)
    
    # Find matches
    results = pattern_matcher.find_matches(["test"])
    
    assert len(results) == 0
    assert len(failed_data) == 1
    assert failed_data[0][0] == "test"
    assert "preprocessing" in failed_data[0][1].lower()

def test_find_matches_matching_error(pattern_matcher, mock_cv2, test_template):
    """Test handling matching error."""
    # Setup template
    pattern_matcher.templates["test"] = test_template
    pattern_matcher.template_sizes["test"] = (100, 100)
    
    # Make matchTemplate raise error
    mock_cv2["match"].side_effect = Exception("Matching error")
    
    # Track failed match signal
    failed_data = []
    def on_failed(template, error):
        failed_data.append((template, error))
    pattern_matcher.match_failed.connect(on_failed)
    
    # Find matches
    results = pattern_matcher.find_matches(["test"])
    
    assert len(results) == 0
    assert len(failed_data) == 1
    assert failed_data[0][0] == "test"
    assert "matching failed" in failed_data[0][1].lower()

def test_find_matches_multiple_results(pattern_matcher, mock_cv2, test_template):
    """Test finding multiple matches in different positions."""
    # Setup template
    pattern_matcher.templates["test"] = test_template
    pattern_matcher.template_sizes["test"] = (100, 100)
    
    # Configure mock match results with multiple high-confidence matches
    mock_cv2["match"].return_value = np.zeros((300, 300))  # Base result matrix
    
    # Configure minMaxLoc to return different positions in sequence
    mock_cv2["minmax"].side_effect = [
        (0.0, 0.98, (0, 0), (250, 250)),  # First match
        (0.0, 0.97, (0, 0), (150, 150)),  # Second match
        (0.0, 0.96, (0, 0), (50, 50)),    # Third match
        (0.0, 0.94, (0, 0), (0, 0))       # Below threshold - stops loop
    ]
    
    # Track match signals
    match_data = []
    def on_match(template, confidence, position):
        match_data.append((template, confidence, position))
    pattern_matcher.match_found.connect(on_match)
    
    # Find matches
    results = pattern_matcher.find_matches(["test"])
    
    # Verify we got all matches
    assert len(results) == 3
    assert len(match_data) == 3
    
    # Verify match properties
    confidences = [0.98, 0.97, 0.96]
    positions = [(250, 250), (150, 150), (50, 50)]
    
    for i, result in enumerate(results):
        assert result.template_name == "test"
        assert result.confidence == confidences[i]
        assert result.position.x() == int(positions[i][0] + 50)  # +50 for center (template width/2)
        assert result.position.y() == int(positions[i][1] + 50)  # +50 for center (template height/2)
        
        # Verify signal data
        assert match_data[i][0] == "test"  # template name
        assert match_data[i][1] == confidences[i]  # confidence
        assert isinstance(match_data[i][2], QPoint)  # position

def test_find_matches_dpi_scaling(pattern_matcher, mock_cv2, test_template, qapp):
    """Test handling DPI scaling in match results."""
    # Setup template
    pattern_matcher.templates["test"] = test_template
    pattern_matcher.template_sizes["test"] = (100, 100)
    
    # Mock capture manager
    test_image = np.zeros((200, 200, 3), dtype=np.uint8)
    pattern_matcher.capture_manager.capture_window.return_value = test_image
    pattern_matcher.capture_manager.preprocess_image.return_value = cv2.cvtColor(test_image, cv2.COLOR_BGR2GRAY)
    pattern_matcher.capture_manager.dpi_scale = 1.5
    
    # Configure mock match results
    mock_cv2["match"].return_value = np.array([[0.96]])
    mock_cv2["minmax"].return_value = (0.0, 0.96, (0, 0), (100, 100))
    
    # Track match signals
    match_data = []
    def on_match(template, confidence, position):
        match_data.append((template, confidence, position))
    pattern_matcher.match_found.connect(on_match)
    
    # Find matches
    results = pattern_matcher.find_matches(["test"])
    
    # Process Qt events to ensure signals are delivered
    qapp.processEvents()
    
    assert len(results) == 1
    assert len(match_data) == 1
    
    # Calculate expected values
    x, y = 100, 100  # Match position
    w, h = 100, 100  # Template size
    center_x = x + w//2  # 150
    center_y = y + h//2  # 150
    dpi_scale = pattern_matcher.capture_manager.dpi_scale
    
    # Verify scaled position (center point)
    assert results[0].position.x() == int(center_x * dpi_scale)  # 150 * 1.5 = 225
    assert results[0].position.y() == int(center_y * dpi_scale)  # 150 * 1.5 = 225
    
    # Verify scaled rectangle
    assert results[0].rect.x() == int(x * dpi_scale)  # 100 * 1.5 = 150
    assert results[0].rect.y() == int(y * dpi_scale)  # 100 * 1.5 = 150
    assert results[0].rect.width() == int(w * dpi_scale)  # 100 * 1.5 = 150
    assert results[0].rect.height() == int(h * dpi_scale)  # 100 * 1.5 = 150
    
    # Verify signal data
    assert match_data[0][0] == "test"  # template name
    assert match_data[0][1] == 0.96  # confidence
    assert isinstance(match_data[0][2], QPoint)  # position
    assert match_data[0][2].x() == int(center_x * dpi_scale)  # Scaled center x
    assert match_data[0][2].y() == int(center_y * dpi_scale)  # Scaled center y