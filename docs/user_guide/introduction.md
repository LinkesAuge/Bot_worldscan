# Introduction to Scout

## What is Scout?

Scout is a powerful automation and computer vision tool designed specifically for the Total Battle game. It helps players detect and interact with game elements, automate repetitive tasks, and analyze game state, making gameplay more efficient and enjoyable.

Unlike simple macro tools, Scout uses advanced computer vision techniques to understand what's happening on the screen and make intelligent decisions based on that information. This allows it to adapt to changing game conditions and perform complex tasks reliably.

## Key Features

### Game Window Detection

Scout can automatically find and track the Total Battle game window, whether it's running in a browser or as a standalone application. This means you don't have to worry about window positioning or resizing - Scout will find the game wherever it is.

- **Browser Support**: Works with Chrome, Firefox, Edge, and other major browsers
- **Standalone App Support**: Works with the Total Battle Windows application
- **Automatic Detection**: Finds the game window by title, class, or process name
- **Multi-Monitor Support**: Works across all connected displays

### Computer Vision

Scout uses multiple detection strategies to identify game elements with high accuracy:

- **Template Matching**: Finds elements by comparing them to known templates
- **Optical Character Recognition (OCR)**: Reads text from the game screen
- **YOLO Object Detection**: Uses deep learning to identify complex elements
- **Result Visualization**: Shows detection results directly on the game screen

### Automation

Create and run sequences of actions to automate repetitive tasks:

- **Action Editor**: Visual editor for creating action sequences
- **Multiple Action Types**: Click, type, wait, condition, loop, and more
- **Smart Waiting**: Wait for specific elements to appear before continuing
- **Error Handling**: Robust error recovery when things don't go as planned
- **Scheduling**: Run sequences at specific times or intervals

### Game State Tracking

Monitor and analyze the game state over time:

- **Resource Tracking**: Monitor resources like gold, wood, stone, etc.
- **Map Visualization**: See territory boundaries and resource locations
- **Buildings and Units**: Track building levels and army compositions
- **State History**: Record state changes over time for analysis

### User Interface

A clean, modern interface designed for ease of use:

- **Tab-based Organization**: Logically organized tabs for different functionality
- **Real-time Visualization**: See detection results as they happen
- **Theme Support**: Light and dark themes for different preferences
- **Multi-language Support**: Available in English and German
- **Keyboard Shortcuts**: Efficient operation using keyboard shortcuts

## System Requirements

### Minimum Requirements

- **Operating System**: Windows 10 (64-bit)
- **Processor**: Dual-core CPU @ 2.0 GHz
- **Memory**: 4 GB RAM
- **Graphics**: DirectX 11 compatible graphics card
- **Display**: 1366x768 resolution
- **Storage**: 500 MB available space
- **Internet**: Broadband internet connection

### Recommended Requirements

- **Operating System**: Windows 10/11 (64-bit)
- **Processor**: Quad-core CPU @ 3.0 GHz or better
- **Memory**: 8 GB RAM or more
- **Graphics**: DirectX 12 compatible graphics card
- **Display**: 1920x1080 resolution or higher
- **Storage**: 1 GB available space
- **Internet**: High-speed broadband internet connection

### Software Requirements

- **Python**: Version 3.9, 3.10, or 3.11
- **Tesseract OCR**: Version 5.5 (for text recognition)
- **CUDA Toolkit**: Version 11.0 or higher (optional, for YOLO detection acceleration)

## Getting Started

Ready to get started with Scout? The next section will guide you through the [installation process](installation.md) and help you set up the application for first use. 