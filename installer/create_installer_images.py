#!/usr/bin/env python3
"""
Create Installer Images

This script creates the bitmap images required for the Scout NSIS installer:
- installer_header.bmp (150x57 pixels): Header image shown on installer pages
- installer_welcome.bmp (164x314 pixels): Welcome/Finish page image
"""

import os
import sys
from pathlib import Path

# Try importing PIL/Pillow
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: Pillow library not found.")
    print("Please install it with: pip install pillow")
    sys.exit(1)

def create_header_image(output_path: str, width: int = 150, height: int = 57):
    """
    Create header bitmap for the installer.
    
    Args:
        output_path: Path to save the bitmap
        width: Image width (default: 150)
        height: Image height (default: 57)
    """
    # Create a new image with white background
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Add a blue bar at the top
    draw.rectangle([(0, 0), (width, 15)], fill=(30, 120, 220))
    
    # Draw "Scout" text
    try:
        # Try to load a font (fall back to default if not available)
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    # Draw "Scout" text
    draw.text((10, 20), "Scout", font=font, fill=(30, 120, 220))
    
    # Draw "Installer" text in smaller font
    try:
        small_font = ImageFont.truetype("arial.ttf", 14)
    except:
        small_font = ImageFont.load_default()
    
    draw.text((70, 25), "Installer", font=small_font, fill=(100, 100, 100))
    
    # Draw version
    draw.text((10, 40), "v1.0.0", font=small_font, fill=(100, 100, 100))
    
    # Save as BMP with no compression
    image.save(output_path, "BMP")
    print(f"Created header image: {output_path}")

def create_welcome_image(output_path: str, width: int = 164, height: int = 314):
    """
    Create welcome bitmap for the installer.
    
    Args:
        output_path: Path to save the bitmap
        width: Image width (default: 164)
        height: Image height (default: 314)
    """
    # Create a new image with gradient background
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Draw gradient-like background (simple version)
    for y in range(height):
        # Create gradient from blue to white
        color_value = max(255 - int(y / height * 200), 55)
        draw.line([(0, y), (width, y)], fill=(color_value, color_value + 50, 255))
    
    # Draw "Scout" text at the top
    try:
        # Try to load a font (fall back to default if not available)
        large_font = ImageFont.truetype("arial.ttf", 24)
    except:
        large_font = ImageFont.load_default()
    
    draw.text((30, 20), "Scout", font=large_font, fill=(0, 0, 120))
    
    # Draw a blue circle icon
    circle_x, circle_y = width // 2, height // 2
    circle_radius = 40
    draw.ellipse(
        [(circle_x - circle_radius, circle_y - circle_radius),
         (circle_x + circle_radius, circle_y + circle_radius)],
        fill=(30, 120, 220)
    )
    
    # Draw "S" in the circle
    try:
        circle_font = ImageFont.truetype("arial.ttf", 50)
    except:
        circle_font = ImageFont.load_default()
    
    draw.text((circle_x - 14, circle_y - 25), "S", font=circle_font, fill=(255, 255, 255))
    
    # Draw version at the bottom
    try:
        small_font = ImageFont.truetype("arial.ttf", 14)
    except:
        small_font = ImageFont.load_default()
    
    draw.text((40, height - 30), "Version 1.0.0", font=small_font, fill=(0, 0, 100))
    
    # Save as BMP with no compression
    image.save(output_path, "BMP")
    print(f"Created welcome image: {output_path}")

def main():
    """Main function."""
    # Get script directory
    script_dir = Path(__file__).parent
    
    # Create header image
    header_path = script_dir / "installer_header.bmp"
    create_header_image(str(header_path))
    
    # Create welcome image
    welcome_path = script_dir / "installer_welcome.bmp"
    create_welcome_image(str(welcome_path))
    
    print("Installer images created successfully.")

if __name__ == "__main__":
    main() 