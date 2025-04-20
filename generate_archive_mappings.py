#!/usr/bin/env python3
"""
Generate mappings between PDF filenames and their archive.gov URLs.
"""

import os
import logging
import json
from archive_mappings import load_archive_mappings
import importlib

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Generate mappings between PDF files and archive.gov URLs"""
    logger.info("Starting archive.gov URL mapping generation")
    
    # Try to import the scan_archive_urls module
    try:
        # Import the module
        scan_archive_urls = importlib.import_module('scan_archive_urls')
        logger.info("Successfully imported scan_archive_urls module")
        
        # Call the main function to generate mappings
        scan_archive_urls.main()
        
    except ImportError:
        logger.error("scan_archive_urls module not found")
        return
    
    # Load the generated mappings
    mappings = load_archive_mappings()
    
    # Verify a few random mappings to make sure they are correct
    verify_mappings(mappings)
    
    # Output summary
    logger.info(f"Generated {len(mappings)} archive mappings and saved to archive_mappings.json")

def verify_mappings(mappings):
    """Verify a sample of mappings to ensure they are correct"""
    if not mappings:
        logger.warning("No mappings to verify")
        return
    
    logger.info("Verifying 5 random mappings:")
    
    # Get up to 5 random keys
    import random
    sample_size = min(5, len(mappings))
    sample_keys = random.sample(list(mappings.keys()), sample_size)
    
    # Print the sample mappings
    for key in sample_keys:
        logger.info(f"  {key}: {mappings[key]}")

if __name__ == "__main__":
    main()