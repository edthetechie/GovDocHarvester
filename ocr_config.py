"""
OCR Configuration - Local settings for Tesseract and Poppler paths
Edit this file to match your installation paths
"""

# Path to Tesseract executable
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Path to Poppler bin directory
POPPLER_PATH = r"C:\Program Files\poppler\bin"

# Number of OCR worker threads to use (increase for faster processing on multi-core systems)
OCR_WORKERS = 2

# Maximum memory usage percentage before pausing (75% is a safe default)
MAX_MEMORY_PERCENT = 75