#!/usr/bin/env python3
"""
Easy PDF Downloader - Download PDFs from pre-configured government websites
"""

import sys
import argparse
from pdf_downloader import PDFDownloader
from config import WEBSITE_CONFIGS, DEFAULT_CONFIG

def list_available_sites():
    """Print a list of available website configurations"""
    print("Available website configurations:")
    for site_id, config in WEBSITE_CONFIGS.items():
        print(f"  {site_id}: {config['description']} ({config['url']})")

def main():
    parser = argparse.ArgumentParser(description="Download PDFs from pre-configured government websites")
    parser.add_argument("site", nargs="?", default=None, help="Site ID to download from (run without args to see list)")
    parser.add_argument("-l", "--list", action="store_true", help="List available site configurations")
    parser.add_argument("-d", "--depth", type=int, help="Override crawl depth")
    parser.add_argument("--delay", type=float, help="Override delay between requests in seconds")
    
    args = parser.parse_args()
    
    # List sites if requested or if no site specified
    if args.list or not args.site:
        list_available_sites()
        return 0
    
    # Check if the site exists
    if args.site not in WEBSITE_CONFIGS:
        print(f"Error: Site '{args.site}' not found in configurations.")
        list_available_sites()
        return 1
    
    # Get the configuration
    config = WEBSITE_CONFIGS[args.site]
    
    # Override parameters if specified
    depth = args.depth if args.depth is not None else config["depth"]
    delay = args.delay if args.delay is not None else config["delay"]
    
    print(f"Downloading PDFs from {config['description']} ({config['url']})")
    print(f"Output directory: {config['output_dir']}")
    print(f"Crawl depth: {depth}")
    print(f"Request delay: {delay}s")
    print()
    
    # Create and run the downloader
    downloader = PDFDownloader(config["url"], config["output_dir"], delay)
    downloader.crawl(depth)
    downloader.download_all_pdfs()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())