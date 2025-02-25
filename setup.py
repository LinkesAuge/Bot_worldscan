from setuptools import setup, find_packages
import os

# Read version from __init__.py
with open(os.path.join("scout", "__init__.py"), "r") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"\'')
            break
    else:
        version = "0.0.0"

# Read long description from README.md
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="scout",
    version=version,
    author="Scout Team",
    author_email="your.email@example.com",
    description="Game automation and detection tool for Total Battle",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/scout",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        "PyQt6>=6.5.0",
        "PyQt6-Qt6>=6.5.0",
        "PyQt6-sip>=13.5.0",
        "numpy>=1.24.0",
        "opencv-python>=4.8.0",
        "pillow>=10.0.0",
        "mss>=9.0.0",
        "pytesseract>=0.3.10",
        "ultralytics>=8.0.0",
        "scikit-image>=0.20.0",
        "pyyaml>=6.0.0",
        "tqdm>=4.65.0",
        "colorlog>=6.7.0",
        "PyQt6-tools>=6.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.3.1",
            "pytest-cov>=4.1.0",
            "pytest-qt>=4.2.0",
            "pytest-xvfb>=2.0.0",
            "ruff>=0.0.267",
            "mypy>=1.3.0",
            "pre-commit>=3.3.2",
            "black>=23.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "scout=scout.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Environment :: X11 Applications :: Qt",
    ],
    keywords="game automation computer-vision detection template-matching ocr",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/scout/issues",
        "Source": "https://github.com/yourusername/scout",
        "Documentation": "https://github.com/yourusername/scout/docs",
    },
) 