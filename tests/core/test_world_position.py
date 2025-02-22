"""Tests for the world position module."""

from scout.core.world_position import WorldPosition

def test_world_position_init() -> None:
    """Test WorldPosition initialization."""
    pos = WorldPosition(x=123, y=456, k=789)
    assert pos.x == 123
    assert pos.y == 456
    assert pos.k == 789

def test_world_position_str() -> None:
    """Test WorldPosition string representation."""
    pos = WorldPosition(x=123, y=456, k=789)
    assert str(pos) == "X=123, Y=456, K=789"

def test_world_position_creation():
    """Test creating a WorldPosition instance."""
    pos = WorldPosition(x=100, y=200, k=1)
    assert pos.x == 100
    assert pos.y == 200
    assert pos.k == 1

def test_world_position_string_representation():
    """Test string representation of WorldPosition."""
    pos = WorldPosition(x=100, y=200, k=1)
    assert str(pos) == "X=100, Y=200, K=1"

def test_world_position_equality():
    """Test WorldPosition equality comparison."""
    pos1 = WorldPosition(x=100, y=200, k=1)
    pos2 = WorldPosition(x=100, y=200, k=1)
    pos3 = WorldPosition(x=200, y=300, k=2)
    
    assert pos1 == pos2
    assert pos1 != pos3

def test_world_position_coordinate_range():
    """Test WorldPosition coordinate range validation."""
    # Valid coordinates
    pos = WorldPosition(x=0, y=0, k=1)
    assert pos.x == 0
    assert pos.y == 0
    
    pos = WorldPosition(x=999, y=999, k=999)
    assert pos.x == 999
    assert pos.y == 999
    
    # Invalid coordinates should still work (no validation in dataclass)
    pos = WorldPosition(x=1000, y=1000, k=1000)
    assert pos.x == 1000
    assert pos.y == 1000 