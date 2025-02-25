# Installation Guide

This guide provides detailed instructions for installing Scout on your system. Scout is primarily developed for Windows and requires several dependencies to function properly.

## Prerequisites

Before installing Scout, ensure your system meets the [system requirements](introduction.md#system-requirements) and install the following prerequisites:

### 1. Python

Scout requires Python 3.9, 3.10, or 3.11. We recommend installing the latest version of Python 3.11 for optimal performance.

1. Download Python from the [official website](https://www.python.org/downloads/).
2. During installation, make sure to check "Add Python to PATH".
3. Verify installation by opening a command prompt and typing:
   ```
   python --version
   ```
   You should see the Python version printed (e.g., `Python 3.11.5`).

### 2. Tesseract OCR

Tesseract is required for optical character recognition (OCR) functionality:

1. Download Tesseract 5.5 for Windows from the [UB-Mannheim repository](https://github.com/UB-Mannheim/tesseract/wiki).
2. Run the installer and follow the prompts.
3. During installation, note the installation path (default is `C:\Program Files\Tesseract-OCR`).
4. Add Tesseract to your system PATH:
   - Right-click on "This PC" or "My Computer" and select "Properties".
   - Click on "Advanced system settings" and then "Environment Variables".
   - Under "System variables", find the PATH variable, select it, and click "Edit".
   - Click "New" and add the Tesseract installation path.
   - Click "OK" to close all dialogs.
5. Verify installation by opening a command prompt and typing:
   ```
   tesseract --version
   ```

### 3. CUDA Toolkit (Optional)

For accelerated YOLO object detection, CUDA Toolkit 11.0 or higher is recommended:

1. Check if your GPU supports CUDA: [CUDA-Enabled GPUs](https://developer.nvidia.com/cuda-gpus)
2. Download CUDA Toolkit from the [NVIDIA website](https://developer.nvidia.com/cuda-downloads).
3. Follow the installation instructions provided by NVIDIA.
4. After installation, verify by opening a command prompt and typing:
   ```
   nvcc --version
   ```

## Installing Scout from Source

### 1. Clone the Repository

1. Install Git if you don't have it already: [Git for Windows](https://git-scm.com/download/win)
2. Open a command prompt and navigate to the directory where you want to install Scout.
3. Clone the repository:
   ```
   git clone https://github.com/yourusername/scout.git
   cd scout
   ```

### 2. Create a Virtual Environment

It's recommended to create a virtual environment to avoid conflicts with other Python packages:

1. Create a virtual environment:
   ```
   python -m venv venv
   ```
2. Activate the virtual environment:
   - On Windows Command Prompt:
     ```
     venv\Scripts\activate
     ```
   - On Windows PowerShell:
     ```
     .\venv\Scripts\Activate.ps1
     ```

### 3. Install Dependencies

With the virtual environment activated, install the required dependencies:

```
pip install -r requirements.txt
```

This will install all necessary Python packages, including:
- PyQt6 for the user interface
- OpenCV for computer vision
- NumPy for numerical operations
- pytesseract for OCR integration

### 4. Configure Scout

1. Copy the example configuration file:
   ```
   copy config.ini.example config.ini
   ```
2. Edit `config.ini` with your preferred text editor to configure Scout.
3. At minimum, set the path to your Tesseract installation:
   ```
   [OCR]
   tesseract_path = C:\Program Files\Tesseract-OCR\tesseract.exe
   ```

## Running Scout

With the virtual environment activated, run Scout:

```
python main.py
```

On first run, Scout will create necessary directories for templates, logs, and other resources.

## Updating Scout

To update Scout to the latest version:

1. Pull the latest changes:
   ```
   git pull
   ```
2. Update dependencies:
   ```
   pip install -r requirements.txt
   ```

## Troubleshooting Installation Issues

### Common Issues

1. **"Python is not recognized as an internal or external command"**
   - Python was not added to PATH during installation.
   - Solution: Reinstall Python and check "Add Python to PATH".

2. **"tesseract is not recognized as an internal or external command"**
   - Tesseract was not added to PATH.
   - Solution: Verify Tesseract installation and add to PATH.

3. **Import errors when running Scout**
   - Missing dependencies or using the wrong Python environment.
   - Solution: Ensure you're using the virtual environment and all dependencies are installed.

4. **PyQt errors**
   - Issues with PyQt installation.
   - Solution: Try reinstalling PyQt6:
     ```
     pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip
     pip install PyQt6
     ```

### Getting Help

If you encounter issues not covered here, check the [Troubleshooting](troubleshooting.md) section or open an issue on the [GitHub repository](https://github.com/yourusername/scout).

## Next Steps

Once Scout is installed, proceed to the [Getting Started](getting_started.md) guide to learn about the user interface and basic usage. 