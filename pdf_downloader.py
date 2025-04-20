#!/usr/bin/env python3
"""
GovDocHarvester - PDF Downloader Module
Download PDF files from government websites
"""

import os
import requests
from bs4 import BeautifulSoup
import urllib.parse
from urllib.parse import urljoin
import argparse
import re
from tqdm import tqdm
import logging
import time
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("download_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PDFDownloader:
    def __init__(self, base_url, output_dir="downloads", delay=1):
        """
        Initialize the PDF downloader
        
        Args:
            base_url (str): The website URL to scan for PDFs
            output_dir (str): Directory to save downloaded files
            delay (float): Delay between requests in seconds
        """
        self.base_url = base_url
        self.output_dir = output_dir
        self.delay = delay
        self.visited_urls = set()
        self.pdf_urls = set()
        self.url_mappings = {}
        
        # Create the output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Load existing archive mappings if available
        self.archive_mappings = {}
        self.archive_mappings_file = "archive_mappings.json"
        if os.path.exists(self.archive_mappings_file):
            try:
                with open(self.archive_mappings_file, 'r') as f:
                    self.archive_mappings = json.load(f)
                logger.info(f"Loaded {len(self.archive_mappings)} existing archive mappings")
            except Exception as e:
                logger.error(f"Error loading archive mappings: {e}")
    
    def download_pdf(self, pdf_url):
        """Download a PDF file from the given URL"""
        try:
            # Create a proper filename from the URL
            parsed_url = urllib.parse.urlparse(pdf_url)
            filename = os.path.basename(parsed_url.path)
            
            # If the filename doesn't have a .pdf extension, add one
            if not filename.lower().endswith('.pdf'):
                filename = f"{filename}.pdf"
            
            # Clean the filename to remove invalid characters
            filename = re.sub(r'[\\/*?:"<>|]', "", filename)
            
            # If filename is empty or just a pdf extension, create a unique name
            if filename in ('', '.pdf'):
                filename = f"document_{len(self.pdf_urls)}.pdf"
                
            file_path = os.path.join(self.output_dir, filename)
            
            # Check if file already exists
            if os.path.exists(file_path):
                logger.info(f"File already exists: {filename}")
                # Even if the file exists, add it to our URL mappings
                self.add_to_archive_mappings(filename, pdf_url)
                return file_path
                
            # Download the file
            logger.info(f"Downloading {pdf_url} to {file_path}")
            response = requests.get(pdf_url, stream=True)
            response.raise_for_status()
            
            # Get total size for progress bar
            total_size = int(response.headers.get('content-length', 0))
            
            # Write the file with progress bar
            with open(file_path, 'wb') as f:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=filename) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            
            logger.info(f"Successfully downloaded {filename}")
            
            # Add to our archive mappings
            self.add_to_archive_mappings(filename, pdf_url)
            
            return file_path
        except Exception as e:
            logger.error(f"Failed to download {pdf_url}: {e}")
            return None
    
    def add_to_archive_mappings(self, filename, pdf_url):
        """Add a mapping between a filename and its archive URL"""
        try:
            # First check if this is from a known archive domain
            parsed_url = urllib.parse.urlparse(pdf_url)
            
            # Common archive domains (update as needed)
            archive_domains = [
                'archives.gov', 
                'www.archives.gov',
                'catalog.archives.gov',
                'archive.org',
                'www.archive.org'
            ]
            
            # If this is from an archive domain, add to mappings
            if any(parsed_url.netloc == domain for domain in archive_domains):
                # Try to extract the base collection URL
                path_parts = parsed_url.path.split('/')
                collection_path = None
                
                # Look for 'details' in the path
                if 'details' in path_parts:
                    idx = path_parts.index('details')
                    if idx + 1 < len(path_parts):
                        collection_id = path_parts[idx + 1]
                        collection_path = f"https://archives.gov/details/{collection_id}"
                
                # If we couldn't find a collection, use the parent directory URL
                if not collection_path:
                    parent_dir = os.path.dirname(parsed_url.path)
                    collection_path = f"{parsed_url.scheme}://{parsed_url.netloc}{parent_dir}"
                
                # Store the mapping
                self.archive_mappings[filename.lower()] = collection_path
                logger.info(f"Added archive mapping: {filename} -> {collection_path}")
                
                # Save the mappings to file
                self.save_archive_mappings()
        except Exception as e:
            logger.error(f"Error adding to archive mappings: {e}")
    
    def save_archive_mappings(self):
        """Save archive URL mappings to a JSON file"""
        try:
            with open(self.archive_mappings_file, 'w') as f:
                json.dump(self.archive_mappings, f, indent=2)
            logger.info(f"Saved {len(self.archive_mappings)} mappings to {self.archive_mappings_file}")
        except Exception as e:
            logger.error(f"Error saving archive mappings: {e}")
    
    def extract_links(self, url):
        """Extract all links from the given URL"""
        try:
            # Don't visit URLs we've already processed
            if url in self.visited_urls:
                return []
            
            logger.info(f"Extracting links from {url}")
            self.visited_urls.add(url)
            
            # Add a delay to be respectful to the server
            time.sleep(self.delay)
            
            response = requests.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            links = []
            
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                full_url = urljoin(url, href)
                
                # Only include links from the same domain
                if full_url.startswith(self.base_url):
                    links.append(full_url)
                
                # If it's a PDF link, add to our PDF collection
                if href.lower().endswith('.pdf'):
                    self.pdf_urls.add(urljoin(url, href))
                    
            return links
        except Exception as e:
            logger.error(f"Error extracting links from {url}: {e}")
            return []
            
    def crawl(self, max_depth=3):
        """
        Crawl the website to find PDF files
        
        Args:
            max_depth (int): Maximum depth to crawl
        """
        logger.info(f"Starting crawl of {self.base_url} with max depth {max_depth}")
        
        current_urls = [self.base_url]
        for depth in range(max_depth):
            logger.info(f"Crawling at depth {depth+1}/{max_depth}")
            next_urls = []
            
            for url in current_urls:
                # Extract links from the current URL
                links = self.extract_links(url)
                next_urls.extend(links)
                
            # Remove duplicates
            current_urls = list(set(next_urls) - self.visited_urls)
            if not current_urls:
                logger.info("No more URLs to crawl")
                break
                
        logger.info(f"Crawl complete. Found {len(self.pdf_urls)} PDF files.")

    def download_all_pdfs(self):
        """Download all PDFs found during crawling"""
        logger.info(f"Starting download of {len(self.pdf_urls)} PDF files")
        
        for pdf_url in self.pdf_urls:
            self.download_pdf(pdf_url)
            time.sleep(self.delay)
            
        logger.info("All PDFs downloaded successfully")
        
        # Save our archive mappings one final time
        self.save_archive_mappings()

def main():
    parser = argparse.ArgumentParser(description="Download PDF files from a website")
    parser.add_argument("url", help="Website URL to scan for PDFs")
    parser.add_argument("-o", "--output", default="downloads", help="Output directory (default: downloads)")
    parser.add_argument("-d", "--depth", type=int, default=3, help="Maximum crawl depth (default: 3)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests in seconds (default: 1.0)")
    parser.add_argument("--archive-domain", default="archives.gov", help="Archive domain to use for mappings (default: archives.gov)")
    
    args = parser.parse_args()
    
    # Create the downloader
    downloader = PDFDownloader(args.url, args.output, args.delay)
    
    # Start crawling and downloading
    downloader.crawl(args.depth)
    downloader.download_all_pdfs()
    
if __name__ == "__main__":
    main()