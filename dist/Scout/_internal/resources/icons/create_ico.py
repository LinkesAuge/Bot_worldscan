#!/usr/bin/env python3
"""
Simple script to create an icon file for Scout application.
This creates a basic icon for development purposes.
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Create a 256x256 image with transparency
size = 256
image = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
draw = ImageDraw.Draw(image)

# Create a blue circle background
circle_color = (30, 120, 220, 255)  # Blue
draw.ellipse((10, 10, size - 10, size - 10), fill=circle_color)

# Draw an 'S' in the center
try:
    # Try to load a font
    font = ImageFont.truetype("arial.ttf", 160)
except:
    # Fall back to default font
    font = ImageFont.load_default()

text_color = (255, 255, 255, 255)  # White
draw.text((size//3, size//6), "S", font=font, fill=text_color)

# Save as .ico file
image.save('scout.ico')
print(f"Icon saved to {os.path.abspath('scout.ico')}")

# Also save a copy to the expected location
icon_path = 'resources/icons/scout.ico'
image.save(icon_path)
print(f"Icon also saved to {os.path.abspath(icon_path)}") 