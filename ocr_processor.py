#!/usr/bin/env python3
"""
PDF OCR Processor - Extract text from scanned PDF documents
"""

import os
import sys
import pytesseract
from pdf2image import convert_from_path
import argparse
from tqdm import tqdm
import logging
import threading
import queue
import time
from config import WEBSITE_CONFIGS
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, STORED
from whoosh.qparser import QueryParser
import shutil

# Import local OCR configuration if available
try:
    from ocr_config import TESSERACT_PATH, POPPLER_PATH, OCR_WORKERS
    
    # Set tesseract path from config if it exists
    if os.path.exists(TESSERACT_PATH):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
        print(f"Using Tesseract from config: {TESSERACT_PATH}")
    
    # Add Poppler to PATH for this session if it exists
    if os.path.exists(POPPLER_PATH):
        os.environ['PATH'] = POPPLER_PATH + os.pathsep + os.environ['PATH']
        print(f"Using Poppler from config: {POPPLER_PATH}")
    
    DEFAULT_WORKERS = OCR_WORKERS
except ImportError:
    # If config doesn't exist, use defaults and look in common locations
    DEFAULT_WORKERS = 2
    
    # Try to set Tesseract path if not in PATH (common Windows locations)
    if os.name == 'nt':  # Windows
        common_tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for path in common_tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ocr_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define schema for search index
schema = Schema(
    path=ID(stored=True),
    filename=STORED,
    title=TEXT(stored=True),
    content=TEXT(stored=True)
)

class PDFOCRProcessor:
    def __init__(self, input_dir, output_dir="ocr_text", index_dir="search_index", num_workers=DEFAULT_WORKERS):
        """
        Initialize the OCR processor
        
        Args:
            input_dir (str): Directory containing PDFs to process
            output_dir (str): Directory to save extracted text
            index_dir (str): Directory for search index
            num_workers (int): Number of parallel OCR workers
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.index_dir = index_dir
        self.num_workers = num_workers
        self.work_queue = queue.Queue()
        
        # Create output directories if they don't exist
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(index_dir, exist_ok=True)
        
        # Create search index if it doesn't exist
        if not os.path.exists(os.path.join(index_dir, "MAIN_WRITELOCK")):
            create_in(index_dir, schema)
    
    def process_pdf(self, pdf_path):
        """
        Extract text from a single PDF file using OCR
        
        Args:
            pdf_path (str): Path to the PDF file
        
        Returns:
            str: Extracted text content
        """
        try:
            base_filename = os.path.basename(pdf_path)
            text_filename = os.path.splitext(base_filename)[0] + ".txt"
            text_path = os.path.join(self.output_dir, text_filename)
            
            # Skip if already processed
            if os.path.exists(text_path):
                logger.info(f"Skipping already processed file: {base_filename}")
                with open(text_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            logger.info(f"Processing {base_filename}")
            
            # Convert PDF to images
            try:
                # Try with poppler path from config if available
                try:
                    poppler_path = POPPLER_PATH
                    if os.path.exists(poppler_path):
                        images = convert_from_path(pdf_path, poppler_path=poppler_path)
                    else:
                        # Fall back to default if config path doesn't exist
                        images = convert_from_path(pdf_path)
                except NameError:
                    # No config file available, use default
                    images = convert_from_path(pdf_path)
            except Exception as e:
                logger.warning(f"Error with default pdf2image settings: {e}")
                
                # If failed, try with explicit poppler path for Windows
                if os.name == 'nt':  # Windows
                    try:
                        # Try to find poppler in common locations
                        poppler_path = None
                        common_poppler_paths = [
                            os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'poppler', 'bin'),
                            os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'poppler', 'bin'),
                            os.path.join(os.path.expanduser('~'), 'poppler', 'bin'),
                            os.path.join(os.path.expanduser('~'), 'Downloads', 'poppler', 'bin'),
                            os.path.join(os.path.expanduser('~'), 'Downloads', 'poppler-windows', 'bin'),
                        ]
                        
                        for path in common_poppler_paths:
                            if os.path.exists(path):
                                poppler_path = path
                                break
                        
                        if poppler_path:
                            logger.info(f"Trying with poppler path: {poppler_path}")
                            images = convert_from_path(pdf_path, poppler_path=poppler_path)
                        else:
                            raise Exception("Poppler not found in common locations")
                    except Exception as inner_e:
                        logger.error(f"Failed to convert PDF with explicit poppler path: {inner_e}")
                        raise
                else:
                    raise
            
            # Extract text from each page
            full_text = ""
            for i, image in enumerate(images):
                text = pytesseract.image_to_string(image)
                full_text += f"\n--- Page {i+1} ---\n{text}\n"
            
            # Save extracted text
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            
            return full_text
        
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}")
            return ""
    
    def worker(self):
        """Worker thread for processing PDFs"""
        while True:
            pdf_path = self.work_queue.get()
            if pdf_path is None:  # Sentinel to stop thread
                self.work_queue.task_done()
                break
            
            try:
                self.process_pdf(pdf_path)
            except Exception as e:
                logger.error(f"Worker error processing {pdf_path}: {e}")
            finally:
                self.work_queue.task_done()
    
    def index_document(self, pdf_path, text_content):
        """
        Index a document in the search index
        
        Args:
            pdf_path (str): Path to the PDF file
            text_content (str): Extracted text content
        """
        try:
            ix = open_dir(self.index_dir)
            writer = ix.writer()
            
            filename = os.path.basename(pdf_path)
            title = os.path.splitext(filename)[0].replace('_', ' ')
            
            writer.add_document(
                path=pdf_path,
                filename=filename,
                title=title,
                content=text_content
            )
            
            writer.commit()
            
        except Exception as e:
            logger.error(f"Error indexing {pdf_path}: {e}")
    
    def process_all(self):
        """Process all PDF files in the input directory"""
        pdf_files = []
        for root, _, files in os.walk(self.input_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {self.input_dir}")
            return
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        # Start worker threads
        threads = []
        for _ in range(self.num_workers):
            t = threading.Thread(target=self.worker)
            t.start()
            threads.append(t)
        
        # Submit jobs to the queue with progress bar
        for pdf_path in tqdm(pdf_files, desc="Queueing PDFs"):
            self.work_queue.put(pdf_path)
        
        # Add sentinels to stop threads
        for _ in range(self.num_workers):
            self.work_queue.put(None)
        
        # Wait for all PDF processing to complete
        self.work_queue.join()
        
        # Wait for all threads to finish
        for t in threads:
            t.join()
        
        # Index all processed documents
        logger.info("Building search index...")
        for pdf_path in tqdm(pdf_files, desc="Indexing documents"):
            text_filename = os.path.splitext(os.path.basename(pdf_path))[0] + ".txt"
            text_path = os.path.join(self.output_dir, text_filename)
            
            if os.path.exists(text_path):
                with open(text_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                self.index_document(pdf_path, text_content)
        
        logger.info("OCR processing and indexing completed")
    
    def rebuild_index(self):
        """Rebuild the search index from existing text files"""
        logger.info("Rebuilding search index...")
        
        # Delete existing index
        if os.path.exists(self.index_dir):
            shutil.rmtree(self.index_dir)
        os.makedirs(self.index_dir, exist_ok=True)
        
        # Create new index
        create_in(self.index_dir, schema)
        
        # Find all text files
        text_files = []
        for root, _, files in os.walk(self.output_dir):
            for file in files:
                if file.lower().endswith('.txt'):
                    text_files.append(os.path.join(root, file))
        
        if not text_files:
            logger.warning(f"No text files found in {self.output_dir}")
            return
        
        logger.info(f"Found {len(text_files)} text files to index")
        
        # Index each text file
        for text_path in tqdm(text_files, desc="Indexing documents"):
            try:
                # Derive the PDF path
                pdf_filename = os.path.splitext(os.path.basename(text_path))[0] + ".pdf"
                pdf_path = os.path.join(self.input_dir, pdf_filename)
                
                # Read the text content
                with open(text_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                
                # Index the document
                self.index_document(pdf_path, text_content)
                
            except Exception as e:
                logger.error(f"Error indexing {text_path}: {e}")
        
        logger.info("Search index rebuild completed")

def main():
    parser = argparse.ArgumentParser(description="OCR PDF files and build search index")
    parser.add_argument("--input", "-i", help="Input directory containing PDF files")
    parser.add_argument("--site", "-s", help="Site ID from config (alternative to --input)")
    parser.add_argument("--output", "-o", default="ocr_text", help="Output directory for extracted text")
    parser.add_argument("--index", default="search_index", help="Directory for search index")
    parser.add_argument("--workers", "-w", type=int, default=2, help="Number of parallel OCR workers")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild search index from existing text files")
    
    args = parser.parse_args()
    
    # Determine input directory
    input_dir = None
    if args.input:
        input_dir = args.input
    elif args.site:
        if args.site in WEBSITE_CONFIGS:
            input_dir = WEBSITE_CONFIGS[args.site]["output_dir"]
        else:
            print(f"Error: Site '{args.site}' not found in configurations.")
            print("Available sites:")
            for site_id in WEBSITE_CONFIGS:
                print(f"  {site_id}: {WEBSITE_CONFIGS[site_id]['description']}")
            return 1
    else:
        print("Error: Either --input or --site must be specified")
        return 1
    
    # Create processor
    processor = PDFOCRProcessor(
        input_dir=input_dir,
        output_dir=args.output,
        index_dir=args.index,
        num_workers=args.workers
    )
    
    # Rebuild index only if requested
    if args.rebuild_index:
        processor.rebuild_index()
    else:
        # Process PDFs and build index
        processor.process_all()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())