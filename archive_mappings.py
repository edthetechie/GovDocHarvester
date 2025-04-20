#!/usr/bin/env python3
"""
Mapping functions for linking PDF files to their archive.gov URLs
"""

import os
import json
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
MAPPINGS_FILE = "archive_mappings.json"

def load_archive_mappings(mapping_file=MAPPINGS_FILE):
    """Load the archive URL mappings from file"""
    mappings = {}
    try:
        if os.path.exists(mapping_file):
            with open(mapping_file, 'r') as f:
                mappings = json.load(f)
            logger.info(f"Loaded {len(mappings)} archive.gov URL mappings from {mapping_file}")
        else:
            logger.warning(f"Mapping file {mapping_file} not found")
    except Exception as e:
        logger.error(f"Error loading archive mappings: {e}")
    
    # Add any manual mappings
    manual_mappings = get_manual_mappings()
    mappings.update(manual_mappings)
    
    logger.info(f"Added manual mappings, total mappings: {len(mappings)}")
    return mappings

def save_archive_mappings(mappings, file_path=MAPPINGS_FILE):
    """
    Save archive URL mappings to JSON file
    
    Args:
        mappings (dict): Archive URL mappings
        file_path (str): Path to the mappings JSON file
    """
    try:
        with open(file_path, 'w') as f:
            json.dump(mappings, f, indent=4)
        logger.info(f"Saved {len(mappings)} archive.gov URL mappings")
    except Exception as e:
        logger.error(f"Error saving archive mappings: {e}")

def get_manual_mappings():
    """Return manual mappings for specific files"""
    return {
        "pol_6-2_us_kennedy_06_05_1968_senator_robert_f._kennedy-part_1_of_6.pdf": "https://archive.gov/details/rfk-assassination-state-department-files",
        "166-12c-1_box_42_jan1970.pdf": "https://archive.gov/details/fbi-rfk-files-box-42-jan1970",
    }

def get_archive_url(filename, mapping_file=MAPPINGS_FILE):
    """Get the archive.gov URL for a filename"""
    if not filename:
        return None
    
    # Load mappings
    mappings = load_archive_mappings(mapping_file)
    
    # Direct lookup
    if filename in mappings:
        return mappings[filename]
    
    # Clean filename and try again
    clean_name = clean_filename(filename)
    if clean_name in mappings:
        return mappings[clean_name]
    
    # Try to extract document ID and pattern match
    doc_id = extract_doc_id(filename)
    if doc_id:
        # Common pattern mappings
        if re.match(r"166-12c-1", doc_id):
            return "https://archive.gov/details/fbi-rfk-files-hq-62-587"
        elif "box_42" in doc_id or "box42" in doc_id:
            return "https://archive.gov/details/fbi-rfk-files-box-42-jan1970"
        elif re.match(r"la[-_\s]?56-156", doc_id, re.IGNORECASE):
            return "https://archive.gov/details/fbi-rfk-files-la-56-156"
        elif re.match(r"la[-_\s]?9-4158", doc_id, re.IGNORECASE):
            return "https://archive.gov/details/fbi-rfk-files-la-9-4158"
        elif re.match(r"pol[-_\s]?6-2", doc_id, re.IGNORECASE):
            return "https://archive.gov/details/rfk-assassination-state-department-files"
    
    return None

def set_archive_url(filename, url, mapping_file=MAPPINGS_FILE):
    """
    Set the archive.gov URL for a document filename
    
    Args:
        filename (str): Filename of the PDF
        url (str): Archive.gov URL
        mapping_file (str): Path to the mappings JSON file
    """
    mappings = load_archive_mappings(mapping_file)
    mappings[filename] = url
    save_archive_mappings(mappings, mapping_file)

def clean_filename(filename):
    """Clean up the filename for better matching"""
    if not filename:
        return ""
    
    # Convert to lowercase
    clean = filename.lower()
    
    # Remove path if present
    clean = os.path.basename(clean)
    
    # Ensure .pdf extension
    if not clean.endswith('.pdf'):
        clean = f"{clean}.pdf"
    
    return clean

def extract_doc_id(filename):
    """Extract document ID from a filename"""
    if not filename:
        return None
    
    # Extract pattern like 166-12c-1 or pol_6-2
    patterns = [
        r'^([^_]+)_',  # Match everything before first underscore
        r'(166-\w+-\d+)',  # FBI file pattern
        r'(pol_?6-2)',  # State dept file pattern
        r'(la[-_]?\d+-\d+)',  # LA field office pattern
        r'box[_\s]?(\d+)'  # Box number pattern
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

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