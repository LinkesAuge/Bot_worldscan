"""Setup configuration for TB Scout package."""

import os
from setuptools import setup, find_packages

# Get version from scout/version.py
version = {}
with open(os.path.join("scout", "version.py")) as fp:
    exec(fp.read(), version)

# Read README.md for long description
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="tb-scout",
    version=version["__version__"],
    author=version["__author__"],
    description="Total Battle Game Assistant",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/tb_scout",
    packages=find_packages(exclude=["tests*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: Microsoft :: Windows",
        "Environment :: Win32 (MS Windows)",
    ],
    python_requires=">=3.9",
    install_requires=[
        "PyQt6>=6.4.0",
        "opencv-python>=4.8.0",
        "numpy>=1.24.0",
        "pytesseract>=0.3.10",
        "mss>=9.0.1",
        "pywin32>=306",
        "pynput>=1.7.6",
        "pydirectinput>=1.0.4",
        "pyautogui>=0.9.54",
        "pygame>=2.5.2",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-cov>=4.1.0",
            "pytest-qt>=4.3.1",
            "pytest-mock>=3.12.0",
            "pytest-timeout>=2.2.0",
            "pytest-xvfb>=3.0.0",
            "pytest-randomly>=3.15.0",
            "pytest-repeat>=0.9.3",
            "coverage>=7.4.1",
            "hypothesis>=6.98.0",
            "ruff>=0.2.1",
            "mypy>=1.8.0",
            "pre-commit>=3.6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "tb-scout=scout.__main__:main",
        ],
    },
    package_data={
        "scout": [
            "config.ini",
            "images/*",
            "sounds/*",
        ],
    },
    include_package_data=True,
    zip_safe=False,
) 