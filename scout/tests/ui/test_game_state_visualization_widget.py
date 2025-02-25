"""
Test Game State Visualization Widget

This module contains tests for the GameStateVisualizationWidget class, which
provides visualization of game state information including resources, map entities,
buildings, and army units.
"""

import unittest
from unittest.mock import MagicMock, patch
import tempfile
import os
import json

from PyQt6.QtWidgets import QApplication, QTabWidget
from PyQt6.QtCore import Qt, QTimer

from scout.core.game.game_service_interface import GameServiceInterface
from scout.ui.widgets.game_state_visualization_widget import (
    GameStateVisualizationWidget, ResourcesView, MapView, BuildingsView, ArmyView
)


class TestGameStateVisualizationWidget(unittest.TestCase):
    """
    Test suite for the GameStateVisualizationWidget class.
    
    This class tests functionality such as:
    - Tab-based organization of different views
    - Displaying game state data across views
    - Refreshing visualizations based on game state changes
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up the application for all tests."""
        # Create QApplication instance if not already created
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up each test."""
        # Create mock game service
        self.game_service = MagicMock(spec=GameServiceInterface)
        
        # Configure mock game service with sample data
        self.sample_resources = {
            'gold': 1000,
            'food': 500,
            'wood': 750,
            'stone': 300,
            'production': {
                'gold': 10,
                'food': 5,
                'wood': 7,
                'stone': 3
            }
        }
        
        self.sample_map = {
            'size': {'width': 1000, 'height': 1000},
            'entities': [
                {'id': 1, 'type': 'building', 'name': 'Town Center', 'x': 100, 'y': 100, 'owner': 'player'},
                {'id': 2, 'type': 'resource', 'name': 'Gold Mine', 'x': 200, 'y': 150, 'remaining': 5000},
                {'id': 3, 'type': 'unit', 'name': 'Worker', 'x': 120, 'y': 120, 'owner': 'player'}
            ]
        }
        
        self.sample_buildings = [
            {'id': 1, 'name': 'Town Center', 'level': 5, 'position': {'x': 100, 'y': 100}, 'health': 1000},
            {'id': 4, 'name': 'Barracks', 'level': 3, 'position': {'x': 150, 'y': 120}, 'health': 800}
        ]
        
        self.sample_army = {
            'units': [
                {'id': 3, 'name': 'Worker', 'count': 10, 'attack': 1, 'defense': 1},
                {'id': 5, 'name': 'Swordsman', 'count': 5, 'attack': 5, 'defense': 3}
            ],
            'total_attack': 30,
            'total_defense': 25
        }
        
        self.sample_game_data = {
            'resources': self.sample_resources,
            'map': self.sample_map,
            'buildings': self.sample_buildings,
            'army': self.sample_army
        }
        
        # Mock get_game_state method
        self.game_service.get_game_state = MagicMock(return_value=self.sample_game_data)
        
        # Create widget
        self.widget = GameStateVisualizationWidget(self.game_service)
    
    def tearDown(self):
        """Clean up after each test."""
        self.widget.deleteLater()
    
    def test_initialization(self):
        """Test widget initialization."""
        # Check that tab widget exists
        self.assertTrue(hasattr(self.widget, '_tabs'))
        self.assertIsInstance(self.widget._tabs, QTabWidget)
        
        # Check that all view tabs exist
        self.assertTrue(hasattr(self.widget, '_resources_view'))
        self.assertIsInstance(self.widget._resources_view, ResourcesView)
        
        self.assertTrue(hasattr(self.widget, '_map_view'))
        self.assertIsInstance(self.widget._map_view, MapView)
        
        self.assertTrue(hasattr(self.widget, '_buildings_view'))
        self.assertIsInstance(self.widget._buildings_view, BuildingsView)
        
        self.assertTrue(hasattr(self.widget, '_army_view'))
        self.assertIsInstance(self.widget._army_view, ArmyView)
        
        # Check initial tab count
        self.assertEqual(self.widget._tabs.count(), 4)
    
    def test_refresh(self):
        """Test refreshing the widget with new game state data."""
        # Mock the refresh methods of each view
        self.widget._resources_view.refresh = MagicMock()
        self.widget._map_view.refresh = MagicMock()
        self.widget._buildings_view.refresh = MagicMock()
        self.widget._army_view.refresh = MagicMock()
        
        # Call refresh
        self.widget.refresh()
        
        # Check that game_service.get_game_state was called
        self.game_service.get_game_state.assert_called_once()
        
        # Check that each view's refresh method was called
        self.widget._resources_view.refresh.assert_called_once()
        self.widget._map_view.refresh.assert_called_once()
        self.widget._buildings_view.refresh.assert_called_once()
        self.widget._army_view.refresh.assert_called_once()
    
    def test_set_game_data(self):
        """Test setting game data directly."""
        # Mock the update methods of each view
        self.widget._resources_view.update_data = MagicMock()
        self.widget._map_view.update_data = MagicMock()
        self.widget._buildings_view.update_data = MagicMock()
        self.widget._army_view.update_data = MagicMock()
        
        # Set game data
        self.widget.set_game_data(self.sample_game_data)
        
        # Check that each view's update_data method was called with correct data
        self.widget._resources_view.update_data.assert_called_with(self.sample_resources)
        self.widget._map_view.update_data.assert_called_with(self.sample_map)
        self.widget._buildings_view.update_data.assert_called_with(self.sample_buildings)
        self.widget._army_view.update_data.assert_called_with(self.sample_army)
    
    def test_tab_changed(self):
        """Test handling of tab change events."""
        # Mock the refresh methods of each view
        self.widget._resources_view.refresh = MagicMock()
        self.widget._map_view.refresh = MagicMock()
        self.widget._buildings_view.refresh = MagicMock()
        self.widget._army_view.refresh = MagicMock()
        
        # Simulate tab change to Resources (index 0)
        self.widget._tabs.setCurrentIndex(0)
        self.widget._on_tab_changed(0)
        
        # Only resources view should be refreshed
        self.widget._resources_view.refresh.assert_called_once()
        self.widget._map_view.refresh.assert_not_called()
        self.widget._buildings_view.refresh.assert_not_called()
        self.widget._army_view.refresh.assert_not_called()
        
        # Reset mocks
        self.widget._resources_view.refresh.reset_mock()
        
        # Simulate tab change to Map (index 1)
        self.widget._tabs.setCurrentIndex(1)
        self.widget._on_tab_changed(1)
        
        # Only map view should be refreshed
        self.widget._resources_view.refresh.assert_not_called()
        self.widget._map_view.refresh.assert_called_once()
        self.widget._buildings_view.refresh.assert_not_called()
        self.widget._army_view.refresh.assert_not_called()


class TestResourcesView(unittest.TestCase):
    """
    Test suite for the ResourcesView class.
    
    This class tests the visualization of game resources including:
    - Display of current resource levels
    - Resource production rates
    - Resource trends over time
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up the application for all tests."""
        # Create QApplication instance if not already created
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up each test."""
        # Create view with no game service (will mock data updates)
        self.view = ResourcesView(None)
        
        # Sample resource data
        self.sample_resources = {
            'gold': 1000,
            'food': 500,
            'wood': 750,
            'stone': 300,
            'production': {
                'gold': 10,
                'food': 5,
                'wood': 7,
                'stone': 3
            }
        }
    
    def tearDown(self):
        """Clean up after each test."""
        self.view.deleteLater()
    
    def test_initialization(self):
        """Test view initialization."""
        # Check that table exists
        self.assertTrue(hasattr(self.view, '_resource_table'))
        
        # Check that chart exists
        self.assertTrue(hasattr(self.view, '_trend_chart'))
        
        # Check that update timer exists
        self.assertTrue(hasattr(self.view, '_update_timer'))
    
    def test_update_data(self):
        """Test updating the view with new resource data."""
        # Update data
        self.view.update_data(self.sample_resources)
        
        # Check that resource table has data
        self.assertEqual(self.view._resource_table.rowCount(), 4)  # gold, food, wood, stone
        
        # Check specific cell values
        gold_amt_idx = self.view._resource_table.findItems('Gold', Qt.MatchFlag.MatchExactly)[0].row()
        gold_amt = self.view._resource_table.item(gold_amt_idx, 1).text()
        self.assertEqual(gold_amt, '1000')
        
        gold_prod_idx = self.view._resource_table.findItems('Gold', Qt.MatchFlag.MatchExactly)[0].row()
        gold_prod = self.view._resource_table.item(gold_prod_idx, 2).text()
        self.assertEqual(gold_prod, '+10/h')
    
    def test_add_to_history(self):
        """Test adding resource data to history for trend analysis."""
        # Add initial data
        self.view.update_data(self.sample_resources)
        
        # Check history size
        self.assertEqual(len(self.view._resource_history['gold']), 1)
        self.assertEqual(len(self.view._resource_history['food']), 1)
        
        # Update with new data
        new_resources = {
            'gold': 1050,  # +50
            'food': 520,   # +20
            'wood': 765,   # +15
            'stone': 309,  # +9
            'production': {
                'gold': 10,
                'food': 5,
                'wood': 7,
                'stone': 3
            }
        }
        self.view.update_data(new_resources)
        
        # Check history size
        self.assertEqual(len(self.view._resource_history['gold']), 2)
        self.assertEqual(len(self.view._resource_history['food']), 2)
        
        # Check history values
        self.assertEqual(self.view._resource_history['gold'][0], 1000)
        self.assertEqual(self.view._resource_history['gold'][1], 1050)


class TestMapView(unittest.TestCase):
    """
    Test suite for the MapView class.
    
    This class tests the visualization of the game map including:
    - Display of map entities
    - Interaction with map elements
    - Handling entity selection
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up the application for all tests."""
        # Create QApplication instance if not already created
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up each test."""
        # Create view with no game service (will mock data updates)
        self.view = MapView(None)
        
        # Sample map data
        self.sample_map = {
            'size': {'width': 1000, 'height': 1000},
            'entities': [
                {'id': 1, 'type': 'building', 'name': 'Town Center', 'x': 100, 'y': 100, 'owner': 'player'},
                {'id': 2, 'type': 'resource', 'name': 'Gold Mine', 'x': 200, 'y': 150, 'remaining': 5000},
                {'id': 3, 'type': 'unit', 'name': 'Worker', 'x': 120, 'y': 120, 'owner': 'player'}
            ]
        }
    
    def tearDown(self):
        """Clean up after each test."""
        self.view.deleteLater()
    
    def test_initialization(self):
        """Test view initialization."""
        # Check that scene exists
        self.assertTrue(hasattr(self.view, '_scene'))
        
        # Check that view exists
        self.assertTrue(hasattr(self.view, '_map_view'))
        
        # Check that entity items dict exists
        self.assertTrue(hasattr(self.view, '_entity_items'))
        self.assertEqual(len(self.view._entity_items), 0)
    
    def test_update_data(self):
        """Test updating the view with new map data."""
        # Update data
        self.view.update_data(self.sample_map)
        
        # Check that entities were added to the scene
        self.assertEqual(len(self.view._entity_items), 3)
    
    def test_entity_selected(self):
        """Test entity selection handling."""
        # Create mock for entity_selected signal
        mock_callback = MagicMock()
        self.view.entity_selected.connect(mock_callback)
        
        # Update data
        self.view.update_data(self.sample_map)
        
        # Get entity by ID
        entity_id = 1  # Town Center
        
        # Simulate entity selection
        self.view._on_entity_selected(entity_id)
        
        # Check that signal was emitted with correct entity data
        expected_entity = self.sample_map['entities'][0]
        mock_callback.assert_called_once()
        args = mock_callback.call_args[0]
        self.assertEqual(args[0]['id'], expected_entity['id'])
        self.assertEqual(args[0]['name'], expected_entity['name'])


class TestBuildingsView(unittest.TestCase):
    """
    Test suite for the BuildingsView class.
    
    This class tests the visualization of game buildings including:
    - Display of building data
    - Building level and status information
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up the application for all tests."""
        # Create QApplication instance if not already created
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up each test."""
        # Create view with no game service (will mock data updates)
        self.view = BuildingsView(None)
        
        # Sample buildings data
        self.sample_buildings = [
            {'id': 1, 'name': 'Town Center', 'level': 5, 'position': {'x': 100, 'y': 100}, 'health': 1000},
            {'id': 4, 'name': 'Barracks', 'level': 3, 'position': {'x': 150, 'y': 120}, 'health': 800}
        ]
    
    def tearDown(self):
        """Clean up after each test."""
        self.view.deleteLater()
    
    def test_initialization(self):
        """Test view initialization."""
        # Check that table exists
        self.assertTrue(hasattr(self.view, '_buildings_table'))
        
        # Check that detail panel exists
        self.assertTrue(hasattr(self.view, '_detail_panel'))
    
    def test_update_data(self):
        """Test updating the view with new buildings data."""
        # Update data
        self.view.update_data(self.sample_buildings)
        
        # Check that buildings table has data
        self.assertEqual(self.view._buildings_table.rowCount(), 2)
        
        # Check specific cell values for Town Center
        row = 0  # assuming first row is Town Center
        name = self.view._buildings_table.item(row, 0).text()
        level = self.view._buildings_table.item(row, 1).text()
        
        self.assertEqual(name, 'Town Center')
        self.assertEqual(level, '5')
    
    def test_building_selected(self):
        """Test building selection handling."""
        # Update data
        self.view.update_data(self.sample_buildings)
        
        # Simulate row selection
        self.view._buildings_table.selectRow(0)
        self.view._on_building_selected()
        
        # Check that selected building was set
        self.assertIsNotNone(self.view._selected_building)
        self.assertEqual(self.view._selected_building['name'], 'Town Center')
        self.assertEqual(self.view._selected_building['level'], 5)


class TestArmyView(unittest.TestCase):
    """
    Test suite for the ArmyView class.
    
    This class tests the visualization of army information including:
    - Display of unit types and counts
    - Army strength metrics
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up the application for all tests."""
        # Create QApplication instance if not already created
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up each test."""
        # Create view with no game service (will mock data updates)
        self.view = ArmyView(None)
        
        # Sample army data
        self.sample_army = {
            'units': [
                {'id': 3, 'name': 'Worker', 'count': 10, 'attack': 1, 'defense': 1},
                {'id': 5, 'name': 'Swordsman', 'count': 5, 'attack': 5, 'defense': 3}
            ],
            'total_attack': 30,
            'total_defense': 25
        }
    
    def tearDown(self):
        """Clean up after each test."""
        self.view.deleteLater()
    
    def test_initialization(self):
        """Test view initialization."""
        # Check that units table exists
        self.assertTrue(hasattr(self.view, '_units_table'))
        
        # Check that summary label exists
        self.assertTrue(hasattr(self.view, '_summary_label'))
    
    def test_update_data(self):
        """Test updating the view with new army data."""
        # Update data
        self.view.update_data(self.sample_army)
        
        # Check that units table has data
        self.assertEqual(self.view._units_table.rowCount(), 2)
        
        # Check specific cell values for Worker
        row = 0  # assuming first row is Worker
        name = self.view._units_table.item(row, 0).text()
        count = self.view._units_table.item(row, 1).text()
        
        self.assertEqual(name, 'Worker')
        self.assertEqual(count, '10')
        
        # Check summary label
        summary_text = self.view._summary_label.text()
        self.assertIn('Total Attack: 30', summary_text)
        self.assertIn('Total Defense: 25', summary_text)
    
    def test_unit_count_history(self):
        """Test tracking unit count history."""
        # Update data initially
        self.view.update_data(self.sample_army)
        
        # Check history size
        self.assertEqual(len(self.view._unit_history), 1)
        
        # Check history for specific unit
        worker_history = [h for h in self.view._unit_history[0]['units'] if h['name'] == 'Worker']
        self.assertEqual(len(worker_history), 1)
        self.assertEqual(worker_history[0]['count'], 10)
        
        # Update with new data
        new_army = {
            'units': [
                {'id': 3, 'name': 'Worker', 'count': 12, 'attack': 1, 'defense': 1},  # +2
                {'id': 5, 'name': 'Swordsman', 'count': 7, 'attack': 5, 'defense': 3}  # +2
            ],
            'total_attack': 40,
            'total_defense': 33
        }
        self.view.update_data(new_army)
        
        # Check history size
        self.assertEqual(len(self.view._unit_history), 2)
        
        # Check history for specific unit
        worker_history = [
            h for entry in self.view._unit_history
            for h in entry['units'] if h['name'] == 'Worker'
        ]
        self.assertEqual(len(worker_history), 2)
        self.assertEqual(worker_history[0]['count'], 10)
        self.assertEqual(worker_history[1]['count'], 12)


if __name__ == '__main__':
    unittest.main() 