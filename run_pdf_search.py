#!/usr/bin/env python3
"""
PDF Search System - Main launcher for OCR and search interface
"""

import os
import sys
import argparse
import subprocess
import time
import webbrowser
from config import WEBSITE_CONFIGS

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