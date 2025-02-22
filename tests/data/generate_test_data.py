"""Script to generate test data for tests."""

import os
import cv2
import numpy as np
from pathlib import Path

def generate_test_images():
    """Generate test images for pattern matching tests."""
    # Create test template
    template = np.zeros((50, 50, 3), dtype=np.uint8)
    cv2.rectangle(template, (10, 10), (40, 40), (255, 255, 255), -1)
    cv2.imwrite("tests/data/images/test_template.png", template)
    
    # Create test image with text
    image = np.zeros((100, 300, 3), dtype=np.uint8)
    cv2.putText(
        image,
        "123",
        (50, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2
    )
    cv2.imwrite("tests/data/images/test_text.png", image)
    
    # Create test screenshot
    screenshot = np.zeros((600, 800, 3), dtype=np.uint8)
    cv2.rectangle(screenshot, (100, 100), (200, 200), (255, 255, 255), -1)
    cv2.rectangle(screenshot, (300, 300), (400, 400), (255, 255, 255), -1)
    cv2.putText(
        screenshot,
        "123",
        (150, 150),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 0, 0),
        2
    )
    cv2.imwrite("tests/data/images/test_screenshot.png", screenshot)

def generate_test_sounds():
    """Generate test sound files."""
    # Create empty WAV file
    with open("tests/data/sounds/test_sound.wav", "wb") as f:
        # Write minimal WAV header
        f.write(b"RIFF")  # ChunkID
        f.write(b"\x24\x00\x00\x00")  # ChunkSize (36 bytes)
        f.write(b"WAVE")  # Format
        f.write(b"fmt ")  # Subchunk1ID
        f.write(b"\x10\x00\x00\x00")  # Subchunk1Size (16 bytes)
        f.write(b"\x01\x00")  # AudioFormat (PCM)
        f.write(b"\x01\x00")  # NumChannels (1)
        f.write(b"\x44\xAC\x00\x00")  # SampleRate (44100)
        f.write(b"\x88\x58\x01\x00")  # ByteRate (44100 * 1 * 2)
        f.write(b"\x02\x00")  # BlockAlign (2)
        f.write(b"\x10\x00")  # BitsPerSample (16)
        f.write(b"data")  # Subchunk2ID
        f.write(b"\x00\x00\x00\x00")  # Subchunk2Size (0 bytes)

def main():
    """Generate all test data."""
    # Create directories if they don't exist
    for path in [
        "tests/data/images",
        "tests/data/sounds",
        "tests/data/debug_screenshots",
        "tests/data/logs"
    ]:
        os.makedirs(path, exist_ok=True)
    
    # Generate test data
    generate_test_images()
    generate_test_sounds()
    
    print("Test data generated successfully!")

if __name__ == "__main__":
    main() 