"""
Configuration file for PDF Downloader
Define website configurations here for easy switching
"""

# Website configurations
WEBSITE_CONFIGS = {
    "rfk": {
        "url": "https://www.archives.gov/research/rfk",
        "description": "Robert F. Kennedy Assassination Archives",
        "output_dir": "downloads/rfk",
        "depth": 3,
        "delay": 1.0
    },
    "jfk": {
        "url": "https://www.archives.gov/research/jfk",
        "description": "JFK Assassination Records",
        "output_dir": "downloads/jfk",
        "depth": 3,
        "delay": 1.0
    },
    "911": {
        "url": "https://www.archives.gov/research/9-11",
        "description": "9/11 Commission Records",
        "output_dir": "downloads/911",
        "depth": 3,
        "delay": 1.0
    }
}

# Default configuration
DEFAULT_CONFIG = "rfk"