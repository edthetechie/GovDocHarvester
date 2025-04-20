#!/usr/bin/env python3
"""
Archive URL mapping utility functions.
Handles loading and mapping between PDF filenames and their archives.gov URLs.
"""

import os
import json
import logging
import re
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_archive_mappings(file_path="archive_mappings.json"):
    """
    Load archive URL mappings from a JSON file
    
    Args:
        file_path (str): Path to the mappings JSON file
        
    Returns:
        dict: Dictionary mapping PDF filenames to archives.gov URLs
    """
    mappings = {}
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                mappings = json.load(f)
            logger.info(f"Loaded {len(mappings)} archives.gov URL mappings from {file_path}")
        else:
            logger.warning(f"Archive mappings file not found: {file_path}")
    except Exception as e:
        logger.error(f"Error loading archive mappings: {e}")
    
    # Add manual mappings for common collections
    manual_mappings = {
        "fbi-rfk-files-hq-62-587.pdf": "https://archives.gov/details/fbi-rfk-files-hq-62-587",
        "rfk-assassination-state-department-files.pdf": "https://archives.gov/details/rfk-assassination-state-department-files",
    }
    
    # Add the manual mappings to the loaded mappings
    mappings.update(manual_mappings)
    
    logger.info(f"Added manual mappings, total mappings: {len(mappings)}")
    return mappings

def save_archive_mappings(mappings, file_path="archive_mappings.json"):
    """
    Save archive URL mappings to JSON file
    
    Args:
        mappings (dict): Archive URL mappings
        file_path (str): Path to the mappings JSON file
    """
    try:
        with open(file_path, 'w') as f:
            json.dump(mappings, f, indent=4)
        logger.info(f"Saved {len(mappings)} archives.gov URL mappings")
    except Exception as e:
        logger.error(f"Error saving archive mappings: {e}")

def get_archive_url(filename, mappings=None):
    """
    Get the archives.gov URL for a PDF filename
    
    Args:
        filename (str): PDF filename to lookup
        mappings (dict, optional): Dictionary of existing mappings. If None, will load from file
        
    Returns:
        str or None: The archives.gov URL if found, None otherwise
    """
    # Load mappings if not provided
    if mappings is None:
        mappings = load_archive_mappings()
    
    # Normalize the filename
    clean_filename = filename.lower().replace(' ', '_')
    if not clean_filename.endswith('.pdf'):
        clean_filename += '.pdf'
    
    # Direct lookup
    if clean_filename in mappings:
        return mappings[clean_filename]
    
    # Try to find a pattern match
    return find_mapping_by_pattern(clean_filename, mappings)

def find_mapping_by_pattern(filename, mappings):
    """
    Find a mapping based on pattern matching when exact match not found
    
    Args:
        filename (str): PDF filename to lookup
        mappings (dict): Dictionary of existing mappings
        
    Returns:
        str or None: The archives.gov URL if a pattern match found, None otherwise
    """
    # Common patterns to extract from filenames
    fbi_pattern = re.compile(r'166-12c-1|fbi[-_]rfk|62[-_]587|56[-_]156|box[-_]?42', re.IGNORECASE)
    state_dept_pattern = re.compile(r'pol[_\s]?6|kennedy|rfk|robert[_\s]?f', re.IGNORECASE)
    
    # Collection URLs
    fbi_collection = "https://archives.gov/details/fbi-rfk-files-hq-62-587"
    state_dept_collection = "https://archives.gov/details/rfk-assassination-state-department-files"
    
    # Check for FBI file patterns
    if fbi_pattern.search(filename):
        return fbi_collection
    
    # Check for State Department file patterns
    if state_dept_pattern.search(filename):
        return state_dept_collection
    
    return None

def set_archive_url(filename, url, file_path="archive_mappings.json"):
    """
    Set the archives.gov URL for a document filename
    
    Args:
        filename (str): Filename of the PDF
        url (str): Archives.gov URL
        file_path (str): Path to the mappings JSON file
    """
    mappings = load_archive_mappings(file_path)
    mappings[filename] = url
    save_archive_mappings(mappings, file_path)

def regenerate_mappings():
    """
    Regenerate mappings by calling generate_archive_mappings.py
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import subprocess
        import sys
        
        logger.info("Regenerating archive mappings...")
        result = subprocess.run([sys.executable, "generate_archive_mappings.py"], 
                               capture_output=True, text=True, check=True)
        
        logger.info("Mappings regenerated successfully")
        return True
    
    except Exception as e:
        logger.error(f"Failed to regenerate mappings: {e}")
        return False