#!/usr/bin/env python3
"""
GovDocHarvester - Main launcher for OCR and search interface
"""

import os
import sys
import argparse
import subprocess
import time
import webbrowser
from config import WEBSITE_CONFIGS
import logging
import json
from pathlib import Path
from archive_mappings import get_archive_url
import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("search_app_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import pytesseract
        import pdf2image
        import flask
        import whoosh

        # Set tesseract path from config if available
        try:
            from ocr_config import TESSERACT_PATH
            if os.path.exists(TESSERACT_PATH):
                pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
                print(f"Using Tesseract from: {TESSERACT_PATH}")
        except ImportError:
            pass
            
        # Check if tesseract is installed and in PATH
        try:
            version = pytesseract.get_tesseract_version()
            print(f"Tesseract OCR version: {version}")
        except Exception as e:
            print("Tesseract OCR is not installed or not in PATH")
            print("Please install Tesseract OCR:")
            print("- Windows: https://github.com/UB-Mannheim/tesseract/wiki")
            print("- macOS: brew install tesseract")
            print("- Linux: sudo apt install tesseract-ocr")
            return False

        # Set poppler path from config if available
        try:
            from ocr_config import POPPLER_PATH
            if os.path.exists(POPPLER_PATH):
                os.environ['PATH'] = POPPLER_PATH + os.pathsep + os.environ['PATH']
                print(f"Using Poppler from: {POPPLER_PATH}")
        except ImportError:
            pass
        
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install all required dependencies:")
        print("pip install -r requirements_ocr.txt")
        return False
    
    return True

def list_sites():
    """List available site configurations"""
    print("Available site configurations:")
    for site_id, config in WEBSITE_CONFIGS.items():
        print(f"  {site_id}: {config['description']} ({config['url']})")
        print(f"      Output directory: {config['output_dir']}")

def run_ocr(site_id, workers=2):
    """Run OCR processing on PDFs from a site"""
    if site_id not in WEBSITE_CONFIGS:
        print(f"Error: Site '{site_id}' not found in configurations.")
        list_sites()
        return False
    
    print(f"Running OCR processing for '{site_id}' ({WEBSITE_CONFIGS[site_id]['description']})")
    print(f"This may take a while depending on the number and size of PDF files.")
    
    cmd = [
        sys.executable,
        "ocr_processor.py",
        "--site", site_id,
        "--workers", str(workers)
    ]
    
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        print("Error running OCR processor. Check the log file for details.")
        return False

def generate_url_mappings(domain="archives.gov"):
    """Generate URL mappings for archive.gov or archives.gov domains"""
    logger.info(f"Generating URL mappings with domain: {domain}")
    
    # Update the domain in archive_mappings.py
    update_file_domain("archive_mappings.py", domain)
    
    # Update the domain in scan_archive_urls.py
    update_file_domain("scan_archive_urls.py", domain)
    
    # Run the URL mapping generation script
    try:
        # First try importing the module to use its functionality
        import scan_archive_urls
        logger.info("Successfully imported scan_archive_urls module")
        scan_archive_urls.main()
    except ImportError:
        # Fall back to subprocess execution if import fails
        logger.warning("Failed to import scan_archive_urls module, falling back to subprocess")
        subprocess.run([sys.executable, "generate_archive_mappings.py"], check=True)
    
    # Also try to find actual PDF links on archives.gov
    try:
        subprocess.run([sys.executable, "find_archive_pdfs.py"], check=True)
    except Exception as e:
        logger.error(f"Error running find_archive_pdfs.py: {e}")
    
    # Verify the mappings
    verify_mappings(domain)

def update_file_domain(filename, domain):
    """Update the domain in a file"""
    try:
        if not os.path.exists(filename):
            logger.warning(f"File not found: {filename}")
            return False
            
        with open(filename, 'r') as f:
            content = f.read()
            
        # Replace archive.org with the correct domain
        content = content.replace('archive.org', domain)
        
        # Also handle variations without www prefix
        if 'www.' in domain:
            plain_domain = domain.replace('www.', '')
            content = content.replace(plain_domain, domain)
        else:
            www_domain = f"www.{domain}"
            content = content.replace(www_domain, domain)
            
        with open(filename, 'w') as f:
            f.write(content)
            
        logger.info(f"Updated {filename} to use domain: {domain}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating domain in {filename}: {e}")
        return False

def verify_mappings(domain="archives.gov"):
    """Verify that mappings were generated correctly"""
    try:
        # Load mappings
        from archive_mappings import load_archive_mappings
        mappings = load_archive_mappings()
        
        if len(mappings) == 0:
            logger.warning("No mappings found!")
            return
            
        # Verify a few random mappings
        import random
        sample_size = min(5, len(mappings))
        sample_keys = random.sample(list(mappings.keys()), sample_size)
        
        logger.info(f"Verifying {sample_size} random mappings:")
        for key in sample_keys:
            url = mappings[key]
            logger.info(f"  {key}: {url}")
        
        # Check if the links are valid (if verification needed)
        # This is commented out to avoid making too many requests
        # for key in sample_keys:
        #    url = mappings[key]
        #    try:
        #        response = requests.head(url, timeout=5)
        #        if response.status_code == 200:
        #            logger.info(f"  VALID: {url}")
        #        else:
        #            logger.warning(f"  INVALID ({response.status_code}): {url}")
        #    except Exception as e:
        #        logger.warning(f"  ERROR: {url} - {e}")
    
    except Exception as e:
        logger.error(f"Error verifying mappings: {e}")

def verify_archives_links():
    """Verify that links to archives.gov are valid"""
    # Load mappings
    try:
        from archive_mappings import load_archive_mappings
        mappings = load_archive_mappings()
        
        if len(mappings) == 0:
            print("No mappings found!")
            return
        
        import random
        sample_size = min(10, len(mappings))
        sample_keys = random.sample(list(mappings.keys()), sample_size)
        
        print(f"Testing {sample_size} random archive links...")
        
        valid_count = 0
        invalid_count = 0
        
        for key in sample_keys:
            url = mappings[key]
            try:
                # Use a GET request for the first few bytes instead of HEAD
                # as some servers don't support HEAD properly
                response = requests.get(url, stream=True, timeout=10)
                response.raw.read(1024)  # Read just the first KB
                response.close()
                
                if response.status_code == 200:
                    print(f"✓ VALID: {url}")
                    valid_count += 1
                else:
                    print(f"✗ INVALID ({response.status_code}): {url}")
                    invalid_count += 1
            except Exception as e:
                print(f"✗ ERROR: {url} - {str(e)[:100]}...")
                invalid_count += 1
        
        print(f"\nResults: {valid_count} valid, {invalid_count} invalid links")
        
        if invalid_count > 0:
            print("\nSome links are not valid. You may want to try:")
            print("1. Running with --generate-mappings to regenerate mappings")
            print("2. Running find_archive_pdfs.py to find actual PDF links on archives.gov")
            print("3. Checking if the archives.gov website structure has changed")
    
    except Exception as e:
        print(f"Error verifying links: {e}")

def start_search_interface(host="127.0.0.1", port=5000, debug=False, open_browser=True):
    """Start the search web interface"""
    print(f"Starting search interface at http://{host}:{port}")
    
    # Build command
    cmd = [
        sys.executable, 
        "search_app.py",
        "--host", host,
        "--port", str(port)
    ]
    
    if debug:
        cmd.append("--debug")
    
    # Open browser after a short delay
    if open_browser:
        def open_web_browser():
            time.sleep(1.5)  # Give the server a moment to start
            url = f"http://{host}:{port}"
            print(f"Opening browser at {url}")
            webbrowser.open(url)
        
        import threading
        browser_thread = threading.Thread(target=open_web_browser)
        browser_thread.daemon = True
        browser_thread.start()
    
    # Start the search interface
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        print("Error starting search interface. Check the log file for details.")
        return False
    except KeyboardInterrupt:
        print("\nSearch interface stopped.")
        return True

def main():
    parser = argparse.ArgumentParser(description="PDF OCR and Search System")
    parser.add_argument("--list", "-l", action="store_true", help="List available site configurations")
    parser.add_argument("--ocr", "-o", help="Run OCR processing on PDFs from the specified site")
    parser.add_argument("--search", "-s", action="store_true", help="Start the search web interface")
    parser.add_argument("--workers", "-w", type=int, default=2, help="Number of parallel OCR workers")
    parser.add_argument("--host", default="127.0.0.1", help="Host to run the search interface on")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the search interface on")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--generate-mappings", "-g", action="store_true", help="Regenerate archive URL mappings")
    parser.add_argument("--domain", default="archives.gov", help="Domain to use for archive URLs (default: archives.gov)")
    parser.add_argument("--verify-links", action="store_true", help="Test a sample of archive.gov links to verify they work")
    
    args = parser.parse_args()
    
    # If no arguments provided, show help and list sites
    if len(sys.argv) == 1:
        parser.print_help()
        print("\n")
        list_sites()
        return 0
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # List sites if requested
    if args.list:
        list_sites()
        return 0
    
    # Verify links if requested
    if args.verify_links:
        verify_archives_links()
        return 0
    
    # Generate URL mappings if requested
    if args.generate_mappings:
        success = generate_url_mappings(domain=args.domain)
        if not success:
            return 1
    
    # Run OCR processing if requested
    if args.ocr:
        success = run_ocr(args.ocr, workers=args.workers)
        if not success:
            return 1
        
        # If search interface is also requested, wait a moment before starting it
        if args.search:
            print("\nOCR processing completed. Starting search interface...")
            time.sleep(1)
    
    # Start search interface if requested
    if args.search:
        return 0 if start_search_interface(
            host=args.host, 
            port=args.port, 
            debug=args.debug,
            open_browser=not args.no_browser
        ) else 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())