#!/usr/bin/env python3
"""
Scan Archive.gov URLs to generate mappings for PDF files.
This script searches Archive.gov for RFK assassination records and builds
a mapping between PDF filenames and their original archive.gov URLs.
"""

import os
import json
import requests
from bs4 import BeautifulSoup
import logging
import time
import re
from urllib.parse import urljoin, urlparse, quote_plus
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("archive_scan_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Search queries to find RFK assassination records on archive.gov
SEARCH_QUERIES = [
    "robert kennedy assassination FBI",
    "RFK assassination records",
    "Sirhan Sirhan FBI records",
    "robert kennedy FOIA documents",
    "RFK FOIA documents",
]

# Known archive.gov collections for RFK documents
KNOWN_COLLECTIONS = [
    "https://archive.gov/details/fbi-rfk-files-hq-62-587",
    "https://archive.gov/details/fbi-rfk-files-la-56-156",
    "https://archive.gov/details/fbi-rfk-files-la-9-4158",
    "https://archive.gov/details/fbi-rfk-files-box-42-jan1970",
    "https://archive.gov/details/rfk-assassination-state-department-files"
]

def clean_filename(filename):
    """
    Clean up the filename to make it usable for mapping
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Cleaned filename
    """
    # Replace spaces with underscores
    clean_name = filename.replace(' ', '_')
    
    # Remove special characters
    clean_name = re.sub(r'[\\/*?:"<>|]', "", clean_name)
    
    # Make lowercase for easier matching
    clean_name = clean_name.lower()
    
    # Ensure PDF extension
    if not clean_name.endswith('.pdf'):
        clean_name += '.pdf'
        
    return clean_name

def search_archive_gov(query, max_results=20, delay=1.0):
    """
    Search Archive.gov for the given query
    
    Args:
        query (str): Search query
        max_results (int): Maximum number of results to return
        delay (float): Delay between requests in seconds
        
    Returns:
        list: List of Archive.gov item URLs
    """
    item_urls = []
    logger.info(f"Searching Archive.gov for: {query}")
    
    try:
        # Add delay to be respectful to the server
        time.sleep(delay)
        
        # Encode the search query
        encoded_query = quote_plus(query)
        
        # Construct the search URL
        search_url = f"https://archive.gov/search?query={encoded_query}&sin=TXT"
        
        # Request the search page
        response = requests.get(search_url)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all search result items
        results = soup.find_all('div', {'class': 'item-ia'})
        
        # Extract item URLs
        for item in results[:max_results]:
            # Find the title link
            title_link = item.find('a', {'class': 'txt-dec-none'})
            if title_link and 'href' in title_link.attrs:
                href = title_link['href']
                if href.startswith('/details/'):
                    full_url = f"https://archive.gov{href}"
                    item_urls.append(full_url)
                    logger.info(f"Found item: {full_url}")
        
    except Exception as e:
        logger.error(f"Error searching Archive.gov: {e}")
    
    return item_urls

def scan_collection_page(url, delay=1.0):
    """
    Scan an Archive.gov collection page for downloadable PDF files
    
    Args:
        url (str): Archive.gov collection URL
        delay (float): Delay between requests in seconds
        
    Returns:
        dict: Dictionary mapping PDF filenames to archive.gov URLs
    """
    mappings = {}
    logger.info(f"Scanning collection page: {url}")
    
    try:
        # Add delay to be respectful to the server
        time.sleep(delay)
        
        # Request the page
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for download links
        download_table = soup.find('table', {'class': 'download-table'})
        if download_table:
            for row in download_table.find_all('tr'):
                format_cell = row.find('td', {'class': 'format'})
                download_cell = row.find('td', {'class': 'download'})
                
                # Look for PDF links
                if format_cell and 'PDF' in format_cell.get_text():
                    if download_cell and download_cell.find('a'):
                        download_link = download_cell.find('a').get('href')
                        if download_link:
                            # Get the filename
                            parsed_url = urlparse(download_link)
                            filename = os.path.basename(parsed_url.path)
                            
                            # Clean up the filename
                            clean_name = clean_filename(filename)
                            
                            # Add the mapping
                            mappings[clean_name] = url
                            logger.info(f"Found PDF: {clean_name} -> {url}")
        
        # Look for preview PDFs (sometimes the only available ones)
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if '.pdf' in href.lower():
                # Get the filename
                parsed_url = urlparse(href)
                filename = os.path.basename(parsed_url.path)
                
                # Clean up the filename
                clean_name = clean_filename(filename)
                
                # Add the mapping
                mappings[clean_name] = url
                logger.info(f"Found PDF link: {clean_name} -> {url}")
                
        # Check for item identifier to create a direct mapping
        collection_id = url.split('/')[-1]
        if collection_id:
            # Create some common filename patterns for this collection
            pattern_filenames = [
                f"{collection_id}.pdf",
                f"{collection_id}-full.pdf",
                f"{collection_id}_complete.pdf"
            ]
            
            # Add mappings for these patterns
            for pdf_name in pattern_filenames:
                mappings[pdf_name] = url
                logger.info(f"Added pattern mapping: {pdf_name} -> {url}")
            
    except Exception as e:
        logger.error(f"Error scanning collection page {url}: {e}")
    
    return mappings

def scan_downloaded_pdfs(download_dir="downloads"):
    """
    Scan the downloaded PDF files to get a list of filenames we need to map
    
    Args:
        download_dir (str): Directory containing downloaded PDFs
        
    Returns:
        list: List of PDF filenames
    """
    pdf_filenames = []
    
    for root, dirs, files in os.walk(download_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_filenames.append(file)
                
    logger.info(f"Found {len(pdf_filenames)} downloaded PDF files")
    return pdf_filenames

def scan_ocr_files(ocr_dir="ocr_text"):
    """
    Scan OCR text files to get a list of corresponding PDF filenames
    
    Args:
        ocr_dir (str): Directory containing OCR text files
        
    Returns:
        list: List of PDF filenames
    """
    pdf_filenames = []
    
    if not os.path.exists(ocr_dir):
        logger.warning(f"OCR directory {ocr_dir} does not exist")
        return pdf_filenames
    
    for file in os.listdir(ocr_dir):
        if file.lower().endswith('.txt'):
            pdf_name = file.replace('.txt', '.pdf')
            pdf_filenames.append(pdf_name)
                
    logger.info(f"Found {len(pdf_filenames)} OCR text files with potential PDF mappings")
    return pdf_filenames

def extract_section_info(filename):
    """
    Extract section and part information from a filename
    
    Args:
        filename (str): Filename like "166-12c-1_section_1-part_1_of_5.txt"
        
    Returns:
        tuple: (document_id, section_number, part_number, total_parts) or None if not found
    """
    pattern = r"(.*?)_section_(\d+)-part_(\d+)_of_(\d+)"
    match = re.match(pattern, filename)
    
    if match:
        doc_id = match.group(1)
        section = match.group(2)
        part = match.group(3)
        total = match.group(4)
        return (doc_id, section, part, total)
    
    return None

def create_doc_collection_mappings(filenames):
    """
    Create mappings of document IDs to collections based on the filenames
    
    Args:
        filenames (list): List of filenames
        
    Returns:
        dict: Dictionary mapping document IDs to collections
    """
    mappings = {}
    
    # Common doc ID patterns and their likely collections
    collection_patterns = {
        r"^166-12c-1": "https://archive.gov/details/fbi-rfk-files-hq-62-587",
        r"box[_\s]?42": "https://archive.gov/details/fbi-rfk-files-box-42-jan1970",
        r"^(?:la|los[_\s]angeles)[_\s-]?56-156": "https://archive.gov/details/fbi-rfk-files-la-56-156",
        r"^(?:la|los[_\s]angeles)[_\s-]?9-4158": "https://archive.gov/details/fbi-rfk-files-la-9-4158",
        r"pol[_\s]?6-2": "https://archive.gov/details/rfk-assassination-state-department-files",
    }
    
    for filename in filenames:
        # Try to match patterns
        for pattern, collection in collection_patterns.items():
            if re.search(pattern, filename, re.IGNORECASE):
                # Extract document ID from filename
                doc_id = extract_doc_id_from_filename(filename)
                if doc_id:
                    mappings[doc_id] = collection
                    break
    
    return mappings

def extract_doc_id_from_filename(filename):
    """
    Extract document ID from a filename
    
    Args:
        filename (str): Filename like "166-12c-1_section_1-part_1_of_5.txt"
        
    Returns:
        str or None: Document ID if found, None otherwise
    """
    # Common patterns for document IDs in filenames
    patterns = [
        r'^([^_]+)_', # Matches IDs like "166-12c-1" from "166-12c-1_section_1-part_1_of_5.txt"
        r'(\d+-\w+-\d+)', # Matches patterns like "166-12c-1" anywhere in the filename
        r'box[_\s]?(\d+)', # Matches box numbers like "box_42" or "box42"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, os.path.basename(filename), re.IGNORECASE)
        if match:
            return match.group(1)
            
    return None

def main():
    """
    Main function to scan Archive.gov collections and generate mapping
    """
    mappings = {}
    
    # First, search for RFK assassination records on Archive.gov
    all_item_urls = set()
    for query in SEARCH_QUERIES:
        item_urls = search_archive_gov(query)
        all_item_urls.update(item_urls)
    
    # Add known collections
    all_item_urls.update(KNOWN_COLLECTIONS)
    
    logger.info(f"Found {len(all_item_urls)} unique Archive.gov items to scan")
    
    # Scan each collection page for PDF links
    for url in all_item_urls:
        collection_mappings = scan_collection_page(url)
        mappings.update(collection_mappings)
            
    # Check for files in the downloads directory
    downloaded_pdfs = scan_downloaded_pdfs()
    
    # Check for OCR text files
    ocr_files = scan_ocr_files()
    
    # Create mappings based on document IDs and section info
    all_files = set([os.path.basename(f) for f in downloaded_pdfs + ocr_files])
    doc_collection_mappings = create_doc_collection_mappings(all_files)
    
    # Add mappings for files that don't have direct matches
    for filename in all_files:
        if filename not in mappings:
            # Try to extract document ID
            doc_id = extract_doc_id_from_filename(filename)
            if doc_id and doc_id in doc_collection_mappings:
                mappings[filename] = doc_collection_mappings[doc_id]
                logger.info(f"Mapped based on document ID: {filename} -> {doc_collection_mappings[doc_id]}")
    
    # Add manual mappings for specific files
    manual_mappings = {
        "pol_6-2_us_kennedy_06_05_1968_senator_robert_f._kennedy-part_1_of_6.pdf": "https://archive.gov/details/rfk-assassination-state-department-files",
        "166-12c-1_box_42_jan1970.pdf": "https://archive.gov/details/fbi-rfk-files-box-42-jan1970",
        # Add more manual mappings here if needed
    }
    
    # Add manual mappings
    mappings.update(manual_mappings)
            
    # Output statistics
    total_pdfs = len(all_files)
    mapped_count = sum(1 for pdf in all_files if pdf in mappings)
    percentage = (mapped_count / total_pdfs * 100) if total_pdfs > 0 else 0
    logger.info(f"Successfully mapped {mapped_count} out of {total_pdfs} files ({percentage:.1f}%)")
    
    # Save mappings to JSON file
    output_file = "archive_mappings.json"
    with open(output_file, "w") as f:
        json.dump(mappings, f, indent=2)
    
    logger.info(f"Saved {len(mappings)} mappings to {output_file}")

if __name__ == "__main__":
    main()