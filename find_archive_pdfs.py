#!/usr/bin/env python3
"""
Find actual PDF files on the National Archives website and map them to our local files.

This script helps create accurate mappings between local PDF filenames and their
locations on the archives.gov website by:
1. Scanning archives.gov collections
2. Finding the actual PDF files available there
3. Matching them to our local files based on naming patterns
"""

import os
import requests
from bs4 import BeautifulSoup
import json
import logging
import time
import re
import argparse
from urllib.parse import urljoin, urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("archive_search_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Common collection URLs on archives.gov
COLLECTION_URLS = [
    "https://www.archives.gov/research/jfk/warren-commission-report",
    "https://www.archives.gov/research/jfk/finding-aids",
    "https://www.archives.gov/research/jfk/releases",
    "https://www.archives.gov/research/rfk",
    "https://www.archives.gov/findingaid/doc-search", 
    "https://www.archives.gov/research-room/finding-aids",
    "https://catalog.archives.gov/search?q=rfk%20assassination",
    "https://catalog.archives.gov/search?q=robert%20kennedy%20assassination",
]

# Certificate verification option (set to False only if necessary)
VERIFY_SSL = True

def clean_filename(filename):
    """Clean up a filename for better matching"""
    # Convert to lowercase
    clean = filename.lower()
    
    # Remove common prefixes and extensions
    clean = re.sub(r'\.(pdf|txt)$', '', clean)
    
    # Remove special characters
    clean = re.sub(r'[^a-z0-9]', '', clean)
    
    return clean

def get_local_files(directory="downloads"):
    """Get a list of local PDF files"""
    local_files = []
    
    # Walk through the downloads directory
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.lower().endswith('.pdf'):
                # Get the full path
                filepath = os.path.join(root, filename)
                
                # Get the relative path for cleaner output
                relpath = os.path.relpath(filepath, directory)
                
                local_files.append((filename, filepath, relpath, clean_filename(filename)))
    
    logger.info(f"Found {len(local_files)} local PDF files")
    return local_files

def scan_page(url, local_files, delay=1.0, max_retries=3):
    """Scan a page for PDF links and try to match with local files"""
    mappings = {}
    pdf_links = []
    
    # Retry loop for reliability
    for attempt in range(max_retries):
        try:
            logger.info(f"Scanning {url} (attempt {attempt+1}/{max_retries})")
            
            # Add delay between requests
            if attempt > 0:
                time.sleep(delay * 2)  # Longer delay for retries
            else:
                time.sleep(delay)
            
            # Request the page
            response = requests.get(url, verify=VERIFY_SSL)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Check for PDF files
                if href.lower().endswith('.pdf'):
                    full_url = urljoin(url, href)
                    pdf_links.append(full_url)
                    
                    # Extract the filename from the URL
                    parsed_url = urlparse(full_url)
                    remote_filename = os.path.basename(parsed_url.path)
                    
                    # Try to match with local files
                    clean_remote = clean_filename(remote_filename)
                    
                    # Look for matches
                    for local_name, local_path, local_rel, clean_local in local_files:
                        if clean_remote == clean_local or clean_remote in clean_local or clean_local in clean_remote:
                            # We found a match!
                            mappings[local_name] = full_url
                            logger.info(f"Found match: {local_name} -> {full_url}")
                            break
            
            logger.info(f"Found {len(pdf_links)} PDF links on {url}")
            break  # Success, exit retry loop
            
        except Exception as e:
            logger.error(f"Error scanning {url}: {e}")
            if attempt == max_retries - 1:
                logger.error(f"Failed to scan {url} after {max_retries} attempts")
    
    return mappings, pdf_links

def scan_all_collections(local_files, additional_urls=None):
    """Scan all collection URLs for PDF files"""
    all_mappings = {}
    all_pdf_links = []
    
    # Combine built-in collection URLs with any additional ones
    urls_to_scan = list(COLLECTION_URLS)
    if additional_urls:
        urls_to_scan.extend(additional_urls)
    
    # Deduplicate URLs
    urls_to_scan = list(set(urls_to_scan))
    
    logger.info(f"Scanning {len(urls_to_scan)} collection URLs")
    
    for url in urls_to_scan:
        mappings, pdf_links = scan_page(url, local_files)
        all_mappings.update(mappings)
        all_pdf_links.extend(pdf_links)
        
    # Also check for PDF links on the pages linked from collections
    secondary_urls = set()
    for url in urls_to_scan:
        try:
            response = requests.get(url, verify=VERIFY_SSL)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link['href']
                if not href.lower().endswith('.pdf') and 'archives.gov' in href:
                    full_url = urljoin(url, href)
                    secondary_urls.add(full_url)
        except Exception as e:
            logger.error(f"Error finding secondary URLs from {url}: {e}")
    
    # Limit secondary URLs to avoid too many requests
    secondary_urls = list(secondary_urls)[:20]  # Limit to 20 secondary pages
    
    logger.info(f"Scanning {len(secondary_urls)} secondary URLs")
    
    for url in secondary_urls:
        mappings, pdf_links = scan_page(url, local_files)
        all_mappings.update(mappings)
        all_pdf_links.extend(pdf_links)
    
    return all_mappings, all_pdf_links

def update_archive_mappings(new_mappings):
    """Update the archive_mappings.json file with new mappings"""
    # Load existing mappings if any
    existing_mappings = {}
    if os.path.exists('archive_mappings.json'):
        try:
            with open('archive_mappings.json', 'r') as f:
                existing_mappings = json.load(f)
            logger.info(f"Loaded {len(existing_mappings)} existing mappings")
        except Exception as e:
            logger.error(f"Error loading existing mappings: {e}")
    
    # Update with new mappings
    updated_count = 0
    for filename, url in new_mappings.items():
        existing_mappings[filename.lower()] = url
        updated_count += 1
    
    # Save updated mappings
    try:
        with open('archive_mappings.json', 'w') as f:
            json.dump(existing_mappings, f, indent=2)
        logger.info(f"Updated {updated_count} mappings, total: {len(existing_mappings)}")
    except Exception as e:
        logger.error(f"Error saving updated mappings: {e}")

def main():
    parser = argparse.ArgumentParser(description="Find PDF files on archives.gov and map them to local files")
    parser.add_argument("-d", "--directory", default="downloads", help="Directory containing local PDF files")
    parser.add_argument("-u", "--url", action="append", help="Additional URLs to scan")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests in seconds")
    
    args = parser.parse_args()
    
    # Get list of local files
    local_files = get_local_files(args.directory)
    
    # Scan collections
    new_mappings, pdf_links = scan_all_collections(local_files, args.url)
    
    # Update mappings file
    update_archive_mappings(new_mappings)
    
    logger.info("Mapping complete. PDF links found:")
    for link in sorted(set(pdf_links))[:20]:  # Show top 20 links
        logger.info(f"  {link}")
    
    if len(pdf_links) > 20:
        logger.info(f"  ... and {len(pdf_links) - 20} more")
    
    print(f"Found {len(pdf_links)} PDF links on archives.gov")
    print(f"Created {len(new_mappings)} new mappings between local files and archives.gov URLs")
    print("Mapping data saved to archive_mappings.json")

if __name__ == "__main__":
    main()