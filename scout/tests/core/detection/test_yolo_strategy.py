"""
Tests for the YOLO detection strategy.
"""

import unittest
from unittest.mock import patch, MagicMock, ANY
import numpy as np
import cv2
import os
import tempfile

from scout.core.detection.strategies.yolo_strategy import YOLOStrategy


class TestYOLOStrategy(unittest.TestCase):
    """
    Test suite for the YOLO detection strategy.
    
    These tests mock the underlying detection frameworks to avoid 
    dependency on actual models in the test environment.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary files for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Create a fake model file
        self.model_path = os.path.join(self.temp_dir.name, "model.weights")
        with open(self.model_path, 'w') as f:
            f.write("fake model data")
            
        # Create a fake config file
        self.config_path = os.path.join(self.temp_dir.name, "model.cfg")
        with open(self.config_path, 'w') as f:
            f.write("fake config data")
            
        # Create a fake class names file
        self.class_names_path = os.path.join(self.temp_dir.name, "classes.txt")
        with open(self.class_names_path, 'w') as f:
            f.write("person\ncar\nbicycle\ndog\ncat")
            
        # Create a sample image for testing
        self.test_image = np.zeros((100, 200, 3), dtype=np.uint8)
        # Add some shape to the image (white rectangle)
        cv2.rectangle(self.test_image, (50, 40), (150, 60), (255, 255, 255), -1)
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()
    
    @patch('scout.core.detection.strategies.yolo_strategy.cv2.dnn')
    def test_opencv_initialization(self, mock_dnn):
        """Test initialization with OpenCV DNN."""
        # Mock layer names and unconnected out layers
        mock_net = MagicMock()
        mock_dnn.readNetFromDarknet.return_value = mock_net
        mock_net.getLayerNames.return_value = ['layer1', 'layer2', 'layer3']
        mock_net.getUnconnectedOutLayers.return_value = [1, 3]
        
        # Initialize strategy
        strategy = YOLOStrategy(
            model_path=self.model_path,
            config_path=self.config_path,
            class_names_path=self.class_names_path,
            framework='opencv'
        )
        
        # Verify initialization
        mock_dnn.readNetFromDarknet.assert_called_once_with(self.config_path, self.model_path)
        self.assertEqual(strategy.get_name(), "yolo")
        self.assertEqual(strategy.get_required_params(), [])
        self.assertEqual(len(strategy.class_names), 5)
        self.assertEqual(strategy.class_names[0], "person")
        
    @patch('scout.core.detection.strategies.yolo_strategy.onnxruntime')
    def test_onnx_initialization(self, mock_ort):
        """Test initialization with ONNX runtime."""
        # Mock ONNX session
        mock_session = MagicMock()
        mock_ort.InferenceSession.return_value = mock_session
        
        # Mock input shape
        mock_input = MagicMock()
        mock_input.name = 'input'
        mock_input.shape = [1, 3, 640, 640]
        mock_session.get_inputs.return_value = [mock_input]
        
        # Mock output
        mock_output = MagicMock()
        mock_output.name = 'output'
        mock_session.get_outputs.return_value = [mock_output]
        
        # Initialize strategy
        strategy = YOLOStrategy(
            model_path=self.model_path,
            class_names_path=self.class_names_path,
            framework='onnx'
        )
        
        # Verify initialization
        mock_ort.InferenceSession.assert_called_once_with(self.model_path)
        self.assertEqual(strategy.input_name, 'input')
        self.assertEqual(strategy.input_height, 640)
        self.assertEqual(strategy.input_width, 640)
        self.assertEqual(strategy.output_names, ['output'])
        
    @patch('scout.core.detection.strategies.yolo_strategy.YOLO', create=True)
    def test_ultralytics_initialization(self, mock_yolo_class):
        """Test initialization with Ultralytics YOLO."""
        # Mock YOLO class
        mock_model = MagicMock()
        mock_yolo_class.return_value = mock_model
        
        # Initialize strategy
        strategy = YOLOStrategy(
            model_path=self.model_path,
            class_names_path=self.class_names_path,
            framework='ultralytics'
        )
        
        # Verify initialization
        mock_yolo_class.assert_called_once_with(self.model_path)
        self.assertEqual(strategy.model, mock_model)
        
    def test_invalid_framework(self):
        """Test initialization with invalid framework."""
        with self.assertRaises(ValueError):
            YOLOStrategy(
                model_path=self.model_path,
                framework='invalid'
            )
            
    def test_missing_model(self):
        """Test initialization with missing model."""
        with self.assertRaises(FileNotFoundError):
            YOLOStrategy(
                model_path="nonexistent_model.weights",
                framework='opencv'
            )
            
    @patch('scout.core.detection.strategies.yolo_strategy.cv2.dnn')
    def test_opencv_detection(self, mock_dnn):
        """Test detection using OpenCV DNN."""
        # Mock layer names and unconnected out layers
        mock_net = MagicMock()
        mock_dnn.readNetFromDarknet.return_value = mock_net
        mock_net.getLayerNames.return_value = ['layer1', 'layer2', 'layer3']
        mock_net.getUnconnectedOutLayers.return_value = [1, 3]
        
        # Mock forward pass output - simulate two detections
        # Format: output[detection][x,y,w,h,objectness,class_scores...]
        mock_output = np.zeros((2, 2, 85), dtype=np.float32)
        # First detection: confidence 0.9 for class 0 (person) at (0.5, 0.5, 0.2, 0.2)
        mock_output[0][0] = [0.5, 0.5, 0.2, 0.2, 0.9] + [0.0] * 80
        mock_output[0][0][5] = 0.9  # Class 0 score
        # Second detection: confidence 0.8 for class 1 (car) at (0.7, 0.3, 0.1, 0.1)
        mock_output[1][0] = [0.7, 0.3, 0.1, 0.1, 0.8] + [0.0] * 80
        mock_output[1][0][6] = 0.8  # Class 1 score
        
        mock_net.forward.return_value = mock_output
        
        # Mock NMS boxes - return indices [0, 1]
        mock_dnn.NMSBoxes.return_value = [0, 1]
        
        # Initialize strategy
        strategy = YOLOStrategy(
            model_path=self.model_path,
            config_path=self.config_path,
            class_names_path=self.class_names_path,
            framework='opencv'
        )
        
        # Perform detection
        detections = strategy.detect(self.test_image, {})
        
        # Verify blob and forward pass
        mock_dnn.blobFromImage.assert_called_once()
        mock_net.forward.assert_called_once()
        
        # Verify NMS
        mock_dnn.NMSBoxes.assert_called_once()
        
        # Verify detections (should be 2 results)
        self.assertEqual(len(detections), 2)
        
        # Verify first detection (person)
        person = detections[0]
        self.assertEqual(person['type'], 'object')
        self.assertEqual(person['class_name'], 'person')
        
        # Verify second detection (car)
        car = detections[1]
        self.assertEqual(car['type'], 'object')
        self.assertEqual(car['class_name'], 'car')
        
    @patch('scout.core.detection.strategies.yolo_strategy.onnxruntime')
    def test_onnx_detection(self, mock_ort):
        """Test detection using ONNX runtime."""
        # Mock ONNX session
        mock_session = MagicMock()
        mock_ort.InferenceSession.return_value = mock_session
        
        # Mock input shape
        mock_input = MagicMock()
        mock_input.name = 'input'
        mock_input.shape = [1, 3, 640, 640]
        mock_session.get_inputs.return_value = [mock_input]
        
        # Mock output
        mock_output = MagicMock()
        mock_output.name = 'output'
        mock_session.get_outputs.return_value = [mock_output]
        
        # Mock run output - simulate two detections in YOLOv8 ONNX format
        # Format: [batch, num_detections, [x, y, w, h, confidence, class_id]]
        mock_run_output = [
            np.array([
                [  # batch 0
                    [0.25, 0.25, 0.2, 0.2, 0.9, 0.0],  # Person
                    [0.70, 0.30, 0.1, 0.1, 0.8, 1.0],  # Car
                    [0.00, 0.00, 0.0, 0.0, 0.0, 0.0],  # Padding
                ]
            ])
        ]
        mock_session.run.return_value = mock_run_output
        
        # Initialize strategy
        strategy = YOLOStrategy(
            model_path=self.model_path,
            class_names_path=self.class_names_path,
            framework='onnx'
        )
        
        # Perform detection
        detections = strategy.detect(self.test_image, {})
        
        # Verify session run
        mock_session.run.assert_called_once()
        
        # Verify detections (should be 2 results)
        self.assertEqual(len(detections), 2)
        
        # Verify first detection (person)
        person = detections[0]
        self.assertEqual(person['type'], 'object')
        self.assertEqual(person['class_id'], 0)
        self.assertEqual(person['class_name'], 'person')
        
        # Verify second detection (car)
        car = detections[1]
        self.assertEqual(car['type'], 'object')
        self.assertEqual(car['class_id'], 1)
        self.assertEqual(car['class_name'], 'car')
        
    @patch('scout.core.detection.strategies.yolo_strategy.YOLO', create=True)
    def test_ultralytics_detection(self, mock_yolo_class):
        """Test detection using Ultralytics YOLO."""
        # Mock YOLO model
        mock_model = MagicMock()
        mock_yolo_class.return_value = mock_model
        
        # Mock run output - simulate Results object with boxes
        mock_result = MagicMock()
        mock_result.names = {0: 'person', 1: 'car'}
        
        # Mock boxes with detections
        mock_box1 = MagicMock()
        mock_box1.xyxy = np.array([[10, 20, 60, 80]])  # x1, y1, x2, y2
        mock_box1.conf = np.array([0.9])
        mock_box1.cls = np.array([0])  # person
        
        mock_box2 = MagicMock()
        mock_box2.xyxy = np.array([[100, 30, 150, 70]])  # x1, y1, x2, y2
        mock_box2.conf = np.array([0.8])
        mock_box2.cls = np.array([1])  # car
        
        # Set up boxes
        mock_boxes = MagicMock()
        mock_boxes.__len__ = lambda self: 2
        mock_boxes.__getitem__ = lambda self, idx: [mock_box1, mock_box2][idx]
        mock_result.boxes = mock_boxes
        
        # Set model to return a list with one result
        mock_model.return_value = [mock_result]
        
        # Initialize strategy
        strategy = YOLOStrategy(
            model_path=self.model_path,
            class_names_path=self.class_names_path,
            framework='ultralytics'
        )
        
        # Perform detection
        detections = strategy.detect(self.test_image, {})
        
        # Verify model run
        mock_model.assert_called_once()
        
        # Verify detections (should be 2 results)
        self.assertEqual(len(detections), 2)
        
        # Verify first detection (person)
        person = detections[0]
        self.assertEqual(person['type'], 'object')
        self.assertEqual(person['class_id'], 0)
        self.assertEqual(person['class_name'], 'person')
        self.assertEqual(person['x'], 10)
        self.assertEqual(person['y'], 20)
        self.assertEqual(person['width'], 50)  # 60-10
        self.assertEqual(person['height'], 60)  # 80-20
        
        # Verify second detection (car)
        car = detections[1]
        self.assertEqual(car['type'], 'object')
        self.assertEqual(car['class_id'], 1)
        self.assertEqual(car['class_name'], 'car')
        self.assertEqual(car['x'], 100)
        self.assertEqual(car['y'], 30)
        self.assertEqual(car['width'], 50)  # 150-100
        self.assertEqual(car['height'], 40)  # 70-30
        
    @patch('scout.core.detection.strategies.yolo_strategy.cv2.dnn')
    def test_detection_with_region(self, mock_dnn):
        """Test detection with region specification."""
        # Mock layer names and unconnected out layers
        mock_net = MagicMock()
        mock_dnn.readNetFromDarknet.return_value = mock_net
        mock_net.getLayerNames.return_value = ['layer1', 'layer2', 'layer3']
        mock_net.getUnconnectedOutLayers.return_value = [1, 3]
        
        # Mock a single detection in the output
        mock_output = np.zeros((1, 1, 85), dtype=np.float32)
        mock_output[0][0] = [0.5, 0.5, 0.2, 0.2, 0.9] + [0.0] * 80
        mock_output[0][0][5] = 0.9  # Class 0 score
        mock_net.forward.return_value = mock_output
        
        # Mock NMS boxes - return index 0
        mock_dnn.NMSBoxes.return_value = [0]
        
        # Initialize strategy
        strategy = YOLOStrategy(
            model_path=self.model_path,
            config_path=self.config_path,
            class_names_path=self.class_names_path,
            framework='opencv'
        )
        
        # Define region (top-left corner of image)
        region = {'left': 50, 'top': 40, 'width': 100, 'height': 60}
        
        # Perform detection with region
        detections = strategy.detect(self.test_image, {'region': region})
        
        # Verify detection coordinates are offset by region
        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0]['x'] >= 50, True)
        self.assertEqual(detections[0]['y'] >= 40, True)
        
    @patch('scout.core.detection.strategies.yolo_strategy.cv2.dnn')
    def test_detection_with_class_filter(self, mock_dnn):
        """Test detection with class ID filtering."""
        # Mock layer names and unconnected out layers
        mock_net = MagicMock()
        mock_dnn.readNetFromDarknet.return_value = mock_net
        mock_net.getLayerNames.return_value = ['layer1', 'layer2', 'layer3']
        mock_net.getUnconnectedOutLayers.return_value = [1, 3]
        
        # Mock forward pass output - two detections, different classes
        mock_output = np.zeros((2, 1, 85), dtype=np.float32)
        # Person (class 0)
        mock_output[0][0] = [0.5, 0.5, 0.2, 0.2, 0.9] + [0.0] * 80
        mock_output[0][0][5] = 0.9
        # Car (class 1)
        mock_output[1][0] = [0.7, 0.3, 0.1, 0.1, 0.8] + [0.0] * 80
        mock_output[1][0][6] = 0.8
        
        mock_net.forward.return_value = mock_output
        
        # Mock NMS boxes - return both indices
        mock_dnn.NMSBoxes.return_value = [0, 1]
        
        # Initialize strategy
        strategy = YOLOStrategy(
            model_path=self.model_path,
            config_path=self.config_path,
            class_names_path=self.class_names_path,
            framework='opencv'
        )
        
        # Test with class filter for cars only
        detections = strategy.detect(self.test_image, {'class_ids': [1]})
        
        # Should only return the car detection
        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0]['class_id'], 1)
        self.assertEqual(detections[0]['class_name'], 'car')
        
    def test_letterbox(self):
        """Test letterbox resizing function."""
        # Create a rectangular image (200x100)
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        
        # Initialize strategy (using mock to avoid actual model loading)
        with patch('scout.core.detection.strategies.yolo_strategy.cv2.dnn'):
            with patch('scout.core.detection.strategies.yolo_strategy.os.path.exists', return_value=True):
                strategy = YOLOStrategy(
                    model_path=self.model_path,
                    framework='opencv'
                )
                
                # Resize to square 64x64
                result = strategy._letterbox(img, new_shape=(64, 64))
                
                # Check result dimensions
                self.assertEqual(result.shape[0], 64)  # height
                self.assertEqual(result.shape[1], 64)  # width
                self.assertEqual(result.shape[2], 3)   # channels
                
                # Original image was wider, so there should be padding on top/bottom
                # Check for padding color (default is gray 114)
                self.assertTrue(np.all(result[0:10, 32, :] == [114, 114, 114]))
                self.assertTrue(np.all(result[54:64, 32, :] == [114, 114, 114]))


if __name__ == '__main__':
    unittest.main() 