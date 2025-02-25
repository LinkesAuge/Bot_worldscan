"""
YOLO Detection Strategy

This module provides a concrete implementation of the DetectionStrategy
for YOLO-based object detection.
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2
import logging
import os
import time
from pathlib import Path

from ..strategy import DetectionStrategy

logger = logging.getLogger(__name__)

class YOLOStrategy(DetectionStrategy):
    """
    Strategy for YOLO-based object detection.
    
    This strategy:
    - Uses pre-trained YOLO models (v3-v8 supported)
    - Detects objects in images with bounding boxes
    - Configures confidence thresholds and non-maximum suppression
    - Returns standardized detection results
    """
    
    def __init__(
        self, 
        model_path: str, 
        config_path: Optional[str] = None,
        class_names_path: Optional[str] = None,
        framework: str = 'opencv'
    ):
        """
        Initialize the YOLO strategy.
        
        Args:
            model_path: Path to the YOLO model weights
            config_path: Path to the YOLO model configuration (for DarkNet models)
            class_names_path: Path to text file with class names (one per line)
            framework: Detection framework to use ('opencv', 'onnx', or 'ultralytics')
        """
        self.model_path = os.path.abspath(model_path) if model_path else None
        self.config_path = os.path.abspath(config_path) if config_path else None
        self.class_names_path = os.path.abspath(class_names_path) if class_names_path else None
        self.framework = framework.lower()
        
        # Validate model path
        if not self.model_path or not os.path.exists(self.model_path):
            logger.error(f"YOLO model not found: {self.model_path}")
            raise FileNotFoundError(f"YOLO model not found: {self.model_path}")
            
        # Load class names
        self.class_names = self._load_class_names()
        
        # Initialize model based on framework
        if self.framework == 'opencv':
            self._init_opencv_dnn()
        elif self.framework == 'onnx':
            self._init_onnx()
        elif self.framework == 'ultralytics':
            self._init_ultralytics()
        else:
            logger.error(f"Unsupported framework: {self.framework}")
            raise ValueError(f"Unsupported framework: {self.framework}")
        
        logger.debug(f"YOLO strategy initialized with {self.framework} framework")
    
    def get_name(self) -> str:
        """
        Get the name of this detection strategy.
        
        Returns:
            Strategy name for identification
        """
        return "yolo"
    
    def get_required_params(self) -> List[str]:
        """
        Get the required parameters for this strategy.
        
        Returns:
            List of parameter names that must be provided to detect()
        """
        return []  # No required parameters, all have defaults
    
    def detect(self, image: np.ndarray, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect objects in an image using YOLO.
        
        Args:
            image: Image to analyze
            params: Detection parameters including:
                - confidence_threshold: Minimum confidence for detections (default: 0.5)
                - nms_threshold: Non-maximum suppression threshold (default: 0.4)
                - class_ids: List of class IDs to detect (default: all)
                - region: Region to process {left, top, width, height} (default: full image)
            
        Returns:
            List of detection dictionaries, each containing:
            - 'type': 'object'
            - 'class_id': Numeric class ID
            - 'class_name': Class name (if available)
            - 'confidence': Detection confidence (0-1)
            - 'x', 'y': Top-left corner of bounding box
            - 'width', 'height': Dimensions of bounding box
        """
        # Extract parameters with defaults
        confidence_threshold = params.get('confidence_threshold', 0.5)
        nms_threshold = params.get('nms_threshold', 0.4)
        class_ids_filter = params.get('class_ids', None)
        region = params.get('region', None)
        
        # Process region if specified
        x_offset, y_offset = 0, 0
        if region:
            left, top = region.get('left', 0), region.get('top', 0)
            width, height = region.get('width', 0), region.get('height', 0)
            
            # Make sure coordinates are valid
            if (left >= 0 and top >= 0 and
                width > 0 and height > 0 and
                left + width <= image.shape[1] and
                top + height <= image.shape[0]):
                
                # Extract region and save offsets for coordinate correction
                image = image[top:top+height, left:left+width]
                x_offset, y_offset = left, top
            else:
                logger.warning(f"Invalid region: {region}, using full image")
        
        # Start time for performance measurement
        start_time = time.time()
        
        # Detect using the appropriate framework
        if self.framework == 'opencv':
            detections = self._detect_opencv(image, confidence_threshold, nms_threshold)
        elif self.framework == 'onnx':
            detections = self._detect_onnx(image, confidence_threshold, nms_threshold)
        elif self.framework == 'ultralytics':
            detections = self._detect_ultralytics(image, confidence_threshold, nms_threshold)
        else:
            logger.error(f"Unknown framework: {self.framework}")
            return []
        
        # Filter by class_ids if specified
        if class_ids_filter is not None:
            detections = [d for d in detections if d['class_id'] in class_ids_filter]
        
        # Add offset from region
        for d in detections:
            d['x'] += x_offset
            d['y'] += y_offset
        
        elapsed_time = time.time() - start_time
        logger.debug(f"Detected {len(detections)} objects in {elapsed_time:.3f}s")
        
        return detections
    
    def _load_class_names(self) -> List[str]:
        """
        Load class names from file.
        
        Returns:
            List of class names or None if not available
        """
        if not self.class_names_path or not os.path.exists(self.class_names_path):
            logger.warning(f"Class names file not found: {self.class_names_path}")
            return None
            
        try:
            with open(self.class_names_path, 'r') as f:
                class_names = [line.strip() for line in f.readlines() if line.strip()]
            logger.debug(f"Loaded {len(class_names)} class names")
            return class_names
        except Exception as e:
            logger.error(f"Failed to load class names: {e}")
            return None
    
    def _init_opencv_dnn(self):
        """Initialize OpenCV DNN model for YOLO."""
        try:
            if self.config_path and os.path.exists(self.config_path):
                # DarkNet YOLO (YOLOv3/YOLOv4)
                self.net = cv2.dnn.readNetFromDarknet(self.config_path, self.model_path)
            else:
                # Try to load as other formats
                self.net = cv2.dnn.readNet(self.model_path)
                
            # Get output layer names
            layer_names = self.net.getLayerNames()
            self.output_layers = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
            
            logger.debug(f"Initialized OpenCV DNN with output layers: {self.output_layers}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenCV DNN: {e}")
            raise
    
    def _init_onnx(self):
        """Initialize ONNX model for YOLO."""
        try:
            # Import onnxruntime here to avoid dependency if not used
            import onnxruntime as ort
            
            # Create ONNX inference session
            self.session = ort.InferenceSession(self.model_path)
            
            # Get model metadata
            model_inputs = self.session.get_inputs()
            self.input_name = model_inputs[0].name
            
            # Get expected input shape
            self.input_shape = model_inputs[0].shape
            if len(self.input_shape) == 4:  # NCHW format
                self.input_height = self.input_shape[2]
                self.input_width = self.input_shape[3]
            else:
                logger.warning(f"Unexpected ONNX input shape: {self.input_shape}")
                self.input_height = self.input_width = 640  # Default
                
            # Get model outputs
            model_outputs = self.session.get_outputs()
            self.output_names = [output.name for output in model_outputs]
            
            logger.debug(f"Initialized ONNX model with input: {self.input_name} ({self.input_width}x{self.input_height})")
        except ImportError:
            logger.error("ONNX Runtime not installed. Install with 'pip install onnxruntime'")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize ONNX model: {e}")
            raise
    
    def _init_ultralytics(self):
        """Initialize Ultralytics YOLO model."""
        try:
            # Import ultralytics here to avoid dependency if not used
            from ultralytics import YOLO
            
            # Load YOLO model
            self.model = YOLO(self.model_path)
            
            logger.debug(f"Initialized Ultralytics YOLO model: {self.model_path}")
        except ImportError:
            logger.error("Ultralytics not installed. Install with 'pip install ultralytics'")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Ultralytics model: {e}")
            raise
    
    def _detect_opencv(self, image: np.ndarray, confidence_threshold: float, nms_threshold: float) -> List[Dict[str, Any]]:
        """
        Detect objects using OpenCV DNN.
        
        Args:
            image: Input image
            confidence_threshold: Minimum confidence for detections
            nms_threshold: Non-maximum suppression threshold
            
        Returns:
            List of detection dictionaries
        """
        height, width = image.shape[:2]
        
        # Create blob from image
        blob = cv2.dnn.blobFromImage(image, 1/255.0, (416, 416), swapRB=True, crop=False)
        self.net.setInput(blob)
        
        # Run forward pass
        outputs = self.net.forward(self.output_layers)
        
        # Process outputs
        boxes = []
        confidences = []
        class_ids = []
        
        for output in outputs:
            for detection in output:
                # Extract class scores
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                if confidence > confidence_threshold:
                    # YOLO output format: [x, y, width, height] normalized to 0-1
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    
                    # Rectangle coordinates (top-left corner)
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        
        # Apply non-maximum suppression
        indices = cv2.dnn.NMSBoxes(boxes, confidences, confidence_threshold, nms_threshold)
        
        # Format results
        detections = []
        for i in indices:
            # OpenCV versions compatibility - in OpenCV >= 4.5.4, indices is a 1D tensor
            if isinstance(i, (list, tuple, np.ndarray)):
                i = i[0]
                
            box = boxes[i]
            x, y, w, h = box
            
            # Ensure coordinates are within image bounds
            x = max(0, x)
            y = max(0, y)
            w = min(w, width - x)
            h = min(h, height - y)
            
            class_id = class_ids[i]
            confidence = confidences[i]
            
            class_name = self.class_names[class_id] if self.class_names and class_id < len(self.class_names) else None
            
            detections.append({
                'type': 'object',
                'class_id': class_id,
                'class_name': class_name,
                'confidence': confidence,
                'x': x,
                'y': y,
                'width': w,
                'height': h
            })
            
        return detections
    
    def _detect_onnx(self, image: np.ndarray, confidence_threshold: float, nms_threshold: float) -> List[Dict[str, Any]]:
        """
        Detect objects using ONNX model.
        
        Args:
            image: Input image
            confidence_threshold: Minimum confidence for detections
            nms_threshold: Non-maximum suppression threshold
            
        Returns:
            List of detection dictionaries
        """
        orig_height, orig_width = image.shape[:2]
        
        # Preprocess image
        if hasattr(self, 'input_height') and hasattr(self, 'input_width'):
            input_height, input_width = self.input_height, self.input_width
        else:
            # Default if not specified in ONNX metadata
            input_height, input_width = 640, 640
            
        # Resize and pad image (letterbox)
        img = self._letterbox(image, new_shape=(input_height, input_width))
        
        # Convert to the appropriate format
        img = img.transpose((2, 0, 1))  # HWC to CHW
        img = np.ascontiguousarray(img) / 255.0  # Normalize to 0-1
        img = img.astype(np.float32)
        img = np.expand_dims(img, axis=0)  # Add batch dimension
        
        # Run inference
        outputs = self.session.run(self.output_names, {self.input_name: img})
        
        # Process results
        # This depends on the YOLO version and export format
        # Assuming a YOLOv8 ONNX output format here
        detections = []
        
        # Handle different output formats
        if len(outputs) == 1 and len(outputs[0].shape) == 3:
            # Handle standard output format [batch, num_detections, bbox+score+class]
            boxes = outputs[0][0]
            
            for box in boxes:
                if len(box) >= 6:  # [x, y, w, h, confidence, class_id]
                    confidence = box[4]
                    
                    if confidence > confidence_threshold:
                        class_id = int(box[5])
                        
                        # Convert from normalized coordinates
                        x = int(box[0] * orig_width)
                        y = int(box[1] * orig_height)
                        w = int(box[2] * orig_width)
                        h = int(box[3] * orig_height)
                        
                        # Ensure coordinates are within image bounds
                        x = max(0, x)
                        y = max(0, y)
                        w = min(w, orig_width - x)
                        h = min(h, orig_height - y)
                        
                        class_name = self.class_names[class_id] if self.class_names and class_id < len(self.class_names) else None
                        
                        detections.append({
                            'type': 'object',
                            'class_id': class_id,
                            'class_name': class_name,
                            'confidence': float(confidence),
                            'x': x,
                            'y': y,
                            'width': w,
                            'height': h
                        })
        else:
            logger.warning(f"Unexpected ONNX output format: {[o.shape for o in outputs]}")
        
        return detections
    
    def _detect_ultralytics(self, image: np.ndarray, confidence_threshold: float, nms_threshold: float) -> List[Dict[str, Any]]:
        """
        Detect objects using Ultralytics YOLO.
        
        Args:
            image: Input image
            confidence_threshold: Minimum confidence for detections
            nms_threshold: Non-maximum suppression threshold
            
        Returns:
            List of detection dictionaries
        """
        # Run inference
        results = self.model(image, conf=confidence_threshold, iou=nms_threshold)
        
        # Format results
        detections = []
        
        # Process all results
        for result in results:
            boxes = result.boxes
            
            for i in range(len(boxes)):
                # Get box information
                box = boxes[i]
                x1, y1, x2, y2 = map(int, box.xyxy[0])  # xyxy format (x1, y1, x2, y2)
                confidence = float(box.conf[0])
                class_id = int(box.cls[0]) if hasattr(box, 'cls') else 0
                
                # Calculate width and height
                width = x2 - x1
                height = y2 - y1
                
                # Get class name if available
                class_name = result.names[class_id] if hasattr(result, 'names') else None
                if not class_name and self.class_names and class_id < len(self.class_names):
                    class_name = self.class_names[class_id]
                
                detections.append({
                    'type': 'object',
                    'class_id': class_id,
                    'class_name': class_name,
                    'confidence': confidence,
                    'x': x1,
                    'y': y1,
                    'width': width,
                    'height': height
                })
        
        return detections
    
    def _letterbox(self, img: np.ndarray, new_shape: Tuple[int, int] = (640, 640), color: Tuple[int, int, int] = (114, 114, 114)) -> np.ndarray:
        """
        Resize and pad image while maintaining aspect ratio.
        
        Args:
            img: Input image
            new_shape: Target shape (height, width)
            color: Color for padding
            
        Returns:
            Resized and padded image
        """
        # Resize image to fit within new_shape
        shape = img.shape[:2]  # current shape [height, width]
        if isinstance(new_shape, int):
            new_shape = (new_shape, new_shape)
            
        # Scale ratio (new / old)
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        
        # Compute padding
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # wh padding
        
        # Divide padding into 2 sides
        dw /= 2
        dh /= 2
        
        # Resize
        if shape[::-1] != new_unpad:  # resize
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
            
        # Add padding
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
        
        return img 