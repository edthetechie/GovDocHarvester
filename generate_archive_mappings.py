#!/usr/bin/env python3
"""
GovDocHarvester - Archive.org URL Mapping Generator
Creates mappings between document filenames and their archive.org URLs
"""

import os
import json
import re
import logging
import argparse
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_document_id(filename):
    """
    Extract document identifier from filename
    Examples:
    - 166-12c-1_section_1-part_1_of_5.pdf -> 166-12c-1
    - 166-12c-1_box_42_jan1970.pdf -> 166-12c-1
    """
    # Pattern to match document IDs like "166-12c-1"
    match = re.match(r'^([\d\-\w]+)_', filename)
    if match:
        return match.group(1)
    return None

def get_archive_url(doc_id, filename=None):
    """
    Generate archive.org URL based on document ID
    
    For RFK papers, the format is typically:
    https://archive.org/details/rfkpapers-doc166-12c-1/
    
    If filename is provided, can potentially link directly to that file
    """
    # Normalize document ID to match archive.org format
    normalized_id = doc_id.replace("-", "")
    
    # RFK papers format
    if doc_id.startswith("166"):
        # Base URL for RFK papers
        return f"https://archive.org/details/rfkpapers-doc{doc_id}/"
    
    # Generic format - can be expanded for other collections
    return f"https://archive.org/details/{doc_id}/"

def generate_mappings(ocr_dir="ocr_text", output_file="archive_mappings.json"):
    """
    Generate mappings between OCR text filenames and their archive.org URLs
    """
    mappings = {}
    
    try:
        # Check if directory exists
        if not os.path.exists(ocr_dir):
            logger.error(f"Directory not found: {ocr_dir}")
            return False
            
        # Get list of text files
        text_files = []
        for root, _, files in os.walk(ocr_dir):
            for file in files:
                if file.endswith(".txt"):
                    text_files.append(file)
                    
        logger.info(f"Found {len(text_files)} text files")
        
        # Generate mappings
        for text_file in text_files:
            # Convert .txt filename to original PDF filename
            pdf_filename = text_file.replace(".txt", ".pdf")
            
            # Extract document ID
            doc_id = extract_document_id(text_file)
            if not doc_id:
                logger.warning(f"Could not extract document ID from {text_file}")
                continue
                
            # Generate archive.org URL
            archive_url = get_archive_url(doc_id)
            
            # Add to mappings
            mappings[pdf_filename] = archive_url
            
        # Write mappings to file
        with open(output_file, 'w') as f:
            json.dump(mappings, f, indent=2)
            
        logger.info(f"Generated {len(mappings)} mappings and saved to {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error generating mappings: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Generate mappings between document filenames and archive.org URLs")
    parser.add_argument("--ocr-dir", default="ocr_text", help="Directory containing OCR text files")
    parser.add_argument("--output", default="archive_mappings.json", help="Output JSON file for mappings")
    
    args = parser.parse_args()
    generate_mappings(args.ocr_dir, args.output)

if __name__ == "__main__":
    main()