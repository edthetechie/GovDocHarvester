#!/usr/bin/env python3
"""
Simple wrapper around pdf_downloader.py for pre-configured websites
"""

import argparse
import sys
from pdf_downloader import PDFDownloader
from config import WEBSITE_CONFIGS

def list_available_sites():
    """List available site configurations"""
    print("Available site configurations:")
    for site_id, config in WEBSITE_CONFIGS.items():
        print(f"  {site_id}: {config['description']}")
        print(f"      URL: {config['url']}")
        print(f"      Output directory: {config['output_dir']}")
        print()

def main():
    parser = argparse.ArgumentParser(description="Download PDFs from pre-configured websites")
    parser.add_argument("site", nargs="?", help="Site ID to download from")
    parser.add_argument("--list", "-l", action="store_true", help="List available site configurations")
    parser.add_argument("--depth", "-d", type=int, help="Override crawl depth")
    parser.add_argument("--delay", type=float, help="Override delay between requests in seconds")
    parser.add_argument("--archive-domain", default="archives.gov", 
                      help="Domain to use for archive mappings (default: archives.gov)")
    
    args = parser.parse_args()
    
    if args.list or args.site is None:
        list_available_sites()
        return 0
        
    # Check if the site ID is valid
    if args.site not in WEBSITE_CONFIGS:
        print(f"Error: Site '{args.site}' not found in configurations.")
        print("Use --list to see available sites.")
        return 1
        
    # Get the site configuration
    config = WEBSITE_CONFIGS[args.site]
    
    # Create the downloader
    downloader = PDFDownloader(
        config['url'],
        output_dir=config['output_dir'],
        delay=args.delay if args.delay is not None else config.get('delay', 1.0)
    )
    
    # Start crawling and downloading
    depth = args.depth if args.depth is not None else config.get('depth', 3)
    downloader.crawl(depth)
    downloader.download_all_pdfs()
    
    print(f"Downloaded PDFs from {config['description']}")
    print(f"Files saved to {config['output_dir']}")
    print(f"Archive mappings saved to archive_mappings.json")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())