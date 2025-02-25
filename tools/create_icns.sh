#!/bin/bash
# Create macOS .icns icon file from PNG images
# This script creates an .icns file for macOS from a PNG source image

# Configuration
APP_NAME="Scout"
SOURCE_PNG="resources/icons/scout.png"
OUTPUT_ICNS="resources/icons/scout.icns"
ICONSET_DIR="resources/icons/scout.iconset"

# Display usage
function show_usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --source <png_file>  Source PNG file (default: $SOURCE_PNG)"
    echo "  --output <icns_file> Output ICNS file (default: $OUTPUT_ICNS)"
    echo "  --help               Show this help"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --source)
            SOURCE_PNG="$2"
            shift 2
            ;;
        --output)
            OUTPUT_ICNS="$2"
            shift 2
            ;;
        --help)
            show_usage
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            ;;
    esac
done

# Check if this is running on macOS
if [ "$(uname)" != "Darwin" ]; then
    echo "Error: This script must be run on macOS."
    echo "Current platform: $(uname)"
    exit 1
fi

# Check if iconutil exists
if ! command -v iconutil &> /dev/null; then
    echo "Error: iconutil command not found. This script requires macOS."
    exit 1
fi

# Check if source PNG exists
if [ ! -f "$SOURCE_PNG" ]; then
    echo "Error: Source PNG file not found at $SOURCE_PNG"
    exit 1
fi

# Create icon directory if it doesn't exist
mkdir -p "$(dirname "$OUTPUT_ICNS")"

# Create iconset directory
echo "Creating iconset directory at $ICONSET_DIR..."
mkdir -p "$ICONSET_DIR"

# Generate different icon sizes from the source PNG
echo "Generating icon sizes..."
sips -z 16 16     "$SOURCE_PNG" --out "${ICONSET_DIR}/icon_16x16.png"
sips -z 32 32     "$SOURCE_PNG" --out "${ICONSET_DIR}/icon_16x16@2x.png"
sips -z 32 32     "$SOURCE_PNG" --out "${ICONSET_DIR}/icon_32x32.png"
sips -z 64 64     "$SOURCE_PNG" --out "${ICONSET_DIR}/icon_32x32@2x.png"
sips -z 128 128   "$SOURCE_PNG" --out "${ICONSET_DIR}/icon_128x128.png"
sips -z 256 256   "$SOURCE_PNG" --out "${ICONSET_DIR}/icon_128x128@2x.png"
sips -z 256 256   "$SOURCE_PNG" --out "${ICONSET_DIR}/icon_256x256.png"
sips -z 512 512   "$SOURCE_PNG" --out "${ICONSET_DIR}/icon_256x256@2x.png"
sips -z 512 512   "$SOURCE_PNG" --out "${ICONSET_DIR}/icon_512x512.png"
sips -z 1024 1024 "$SOURCE_PNG" --out "${ICONSET_DIR}/icon_512x512@2x.png"

# Create .icns file from the iconset
echo "Creating ICNS file at $OUTPUT_ICNS..."
iconutil -c icns "$ICONSET_DIR" -o "$OUTPUT_ICNS"

# Clean up the iconset directory
echo "Cleaning up iconset directory..."
rm -rf "$ICONSET_DIR"

echo "ICNS creation complete: $OUTPUT_ICNS"
echo "You can now use this icon in your macOS application bundle." 