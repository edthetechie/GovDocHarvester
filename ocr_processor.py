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
import json
import gc
import psutil
import tempfile
from config import WEBSITE_CONFIGS
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, STORED
from whoosh.qparser import QueryParser
import shutil

# Import local OCR configuration if available
try:
    from ocr_config import TESSERACT_PATH, POPPLER_PATH, OCR_WORKERS, MAX_MEMORY_PERCENT
    
    # Set tesseract path from config if it exists
    if os.path.exists(TESSERACT_PATH):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
        print(f"Using Tesseract from config: {TESSERACT_PATH}")
    
    # Add Poppler to PATH for this session if it exists
    if os.path.exists(POPPLER_PATH):
        os.environ['PATH'] = POPPLER_PATH + os.pathsep + os.environ['PATH']
        print(f"Using Poppler from config: {POPPLER_PATH}")
    
    DEFAULT_WORKERS = OCR_WORKERS
    MAX_MEMORY = MAX_MEMORY_PERCENT if 'MAX_MEMORY_PERCENT' in locals() else 75  # Default to 75% if not in config
except ImportError:
    # If config doesn't exist, use defaults and look in common locations
    DEFAULT_WORKERS = 2
    MAX_MEMORY = 75  # Default max memory usage (75%)
    
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
    def __init__(self, input_dir, output_dir="ocr_text", index_dir="search_index", num_workers=DEFAULT_WORKERS, max_memory_percent=MAX_MEMORY):
        """
        Initialize the OCR processor
        
        Args:
            input_dir (str): Directory containing PDFs to process
            output_dir (str): Directory to save extracted text
            index_dir (str): Directory for search index
            num_workers (int): Number of parallel OCR workers
            max_memory_percent (int): Maximum memory usage percentage before pausing
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.index_dir = index_dir
        self.num_workers = num_workers
        self.max_memory_percent = max_memory_percent
        self.work_queue = queue.Queue()
        self.processed_files = []
        self.error_files = []
        self.progress_file = os.path.join(output_dir, ".ocr_progress.json")
        
        # Create output directories if they don't exist
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(index_dir, exist_ok=True)
        
        # Create search index if it doesn't exist
        if not os.path.exists(os.path.join(index_dir, "MAIN_WRITELOCK")):
            create_in(index_dir, schema)
            
        # Load previously saved progress if it exists
        self.load_progress()
    
    def load_progress(self):
        """Load previously saved progress"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    progress = json.load(f)
                    self.processed_files = progress.get('processed', [])
                    self.error_files = progress.get('errors', [])
                    logger.info(f"Loaded progress: {len(self.processed_files)} files processed, {len(self.error_files)} failed")
            except Exception as e:
                logger.error(f"Error loading progress file: {e}")
    
    def save_progress(self):
        """Save current progress"""
        try:
            with open(self.progress_file, 'w') as f:
                json.dump({
                    'processed': self.processed_files,
                    'errors': self.error_files,
                    'last_update': time.strftime("%Y-%m-%d %H:%M:%S")
                }, f)
        except Exception as e:
            logger.error(f"Error saving progress file: {e}")
    
    def check_memory_usage(self):
        """Check if memory usage is too high"""
        try:
            memory = psutil.virtual_memory()
            memory_used_percent = memory.percent
            
            if memory_used_percent > self.max_memory_percent:
                logger.warning(f"Memory usage high ({memory_used_percent}% > {self.max_memory_percent}%), triggering garbage collection")
                gc.collect()
                
                # If still too high after garbage collection, return True to indicate pause needed
                memory = psutil.virtual_memory()
                memory_used_percent = memory.percent
                if memory_used_percent > self.max_memory_percent:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking memory: {e}")
            return False
    
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
                return self.read_text_file(text_path)
            
            # Skip if in processed list
            if pdf_path in self.processed_files:
                logger.info(f"Skipping file from progress log: {base_filename}")
                return ""
            
            # Skip if in error list
            if pdf_path in self.error_files:
                logger.info(f"Skipping previously failed file: {base_filename}")
                return ""
            
            logger.info(f"Processing {base_filename}")
            
            # Check memory usage before processing
            if self.check_memory_usage():
                logger.warning(f"Memory usage too high, pausing for 5 seconds")
                time.sleep(5)  # Wait for memory to be freed up
                if self.check_memory_usage():  # Check again after pause
                    logger.error("Memory still too high, skipping file")
                    self.error_files.append(pdf_path)
                    self.save_progress()
                    return ""
            
            # Create a temporary directory for this PDF processing
            with tempfile.TemporaryDirectory() as temp_dir:
                # Convert PDF to images
                try:
                    # Try with poppler path from config if available
                    try:
                        poppler_path = POPPLER_PATH
                        if os.path.exists(poppler_path):
                            # Use lower dpi and memory-efficient settings
                            images = convert_from_path(pdf_path, 
                                                      poppler_path=poppler_path, 
                                                      dpi=200,  # Lower DPI
                                                      output_folder=temp_dir,  # Save images to temp folder
                                                      fmt='jpeg',  # Use JPEG format (smaller size)
                                                      use_pdftocairo=True)  # More memory efficient
                        else:
                            # Fall back to default if config path doesn't exist
                            images = convert_from_path(pdf_path, 
                                                      dpi=200, 
                                                      output_folder=temp_dir,
                                                      fmt='jpeg',
                                                      use_pdftocairo=True)
                    except NameError:
                        # No config file available, use default
                        images = convert_from_path(pdf_path, 
                                                dpi=200, 
                                                output_folder=temp_dir,
                                                fmt='jpeg',
                                                use_pdftocairo=True)
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
                                # Try with lower quality settings
                                images = convert_from_path(pdf_path, 
                                                        poppler_path=poppler_path, 
                                                        dpi=150,  # Even lower DPI
                                                        output_folder=temp_dir,
                                                        fmt='jpeg',
                                                        use_pdftocairo=True)
                            else:
                                raise Exception("Poppler not found in common locations")
                        except Exception as inner_e:
                            logger.error(f"Failed to convert PDF with explicit poppler path: {inner_e}")
                            self.error_files.append(pdf_path)
                            self.save_progress()
                            raise
                    else:
                        self.error_files.append(pdf_path)
                        self.save_progress()
                        raise
                
                # Extract text from each page
                full_text = ""
                num_images = len(images)
                
                for i, image in enumerate(images):
                    try:
                        # Check memory again before processing each page
                        if self.check_memory_usage():
                            logger.warning(f"Memory usage too high, pausing for 5 seconds during page processing")
                            time.sleep(5)
                        
                        # Log progress on large documents
                        if num_images > 10 and i % 5 == 0:
                            logger.info(f"Processing page {i+1}/{num_images} of {base_filename}")
                            
                        text = pytesseract.image_to_string(image)
                        full_text += f"\n--- Page {i+1} ---\n{text}\n"
                        
                        # Explicitly delete the image reference to free memory
                        del image
                        if i % 5 == 0:  # Run garbage collection periodically
                            gc.collect()
                            
                    except Exception as page_error:
                        logger.error(f"Error processing page {i+1} of {pdf_path}: {page_error}")
                        full_text += f"\n--- Page {i+1} ---\n[OCR ERROR: {str(page_error)}]\n"
                
                # Force cleanup before saving
                gc.collect()
            
            # Save extracted text
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            
            # Add to processed files list
            self.processed_files.append(pdf_path)
            self.save_progress()
            
            return full_text
        
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}")
            self.error_files.append(pdf_path)
            self.save_progress()
            return ""
    
    def read_text_file(self, text_path):
        """Read a text file with proper error handling"""
        try:
            with open(text_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading text file {text_path}: {e}")
            return ""
    
    def worker(self):
        """Worker thread for processing PDFs"""
        while True:
            try:
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
            except Exception as e:
                logger.error(f"Critical worker error: {e}")
    
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
        
        # Sort files by size (process smaller files first for quicker wins)
        pdf_files.sort(key=lambda x: os.path.getsize(x))
        
        # Filter out already processed files
        unprocessed_files = []
        for pdf_path in pdf_files:
            text_filename = os.path.splitext(os.path.basename(pdf_path))[0] + ".txt"
            text_path = os.path.join(self.output_dir, text_filename)
            
            if not os.path.exists(text_path) and pdf_path not in self.processed_files:
                unprocessed_files.append(pdf_path)
        
        logger.info(f"Found {len(pdf_files)} PDF files, {len(unprocessed_files)} need processing")
        
        if not unprocessed_files:
            logger.info("All files have been processed already!")
            logger.info("Building search index for processed files...")
            self.rebuild_index()
            return
        
        # Start worker threads
        threads = []
        for _ in range(min(self.num_workers, len(unprocessed_files))):  # Don't create more threads than files
            t = threading.Thread(target=self.worker)
            t.daemon = True  # Mark as daemon so they can be killed if needed
            t.start()
            threads.append(t)
        
        # Submit jobs to the queue with progress bar
        try:
            for pdf_path in tqdm(unprocessed_files, desc="Queueing PDFs"):
                self.work_queue.put(pdf_path)
                # Small sleep to allow UI updates and reduce CPU spikes
                time.sleep(0.01)
            
            # Add sentinels to stop threads
            for _ in range(len(threads)):
                self.work_queue.put(None)
            
            # Wait for all PDF processing to complete with timeout and progress updates
            start_time = time.time()
            last_queue_size = self.work_queue.qsize()
            last_update_time = start_time
            
            while not self.work_queue.empty():
                # Check if queue is making progress
                current_queue_size = self.work_queue.qsize()
                current_time = time.time()
                
                # If it's been more than 5 minutes, show progress update
                if current_time - last_update_time > 300:  # 5 minutes
                    files_done = len(unprocessed_files) - current_queue_size
                    percent_done = (files_done / len(unprocessed_files)) * 100
                    elapsed = current_time - start_time
                    estimated_total = elapsed / max(files_done, 1) * len(unprocessed_files)
                    remaining = max(0, estimated_total - elapsed)
                    
                    hours_remaining = int(remaining // 3600)
                    minutes_remaining = int((remaining % 3600) // 60)
                    
                    logger.info(f"Progress: {percent_done:.1f}% ({files_done}/{len(unprocessed_files)}) - " +
                                f"Est. remaining: {hours_remaining}h {minutes_remaining}m")
                    
                    last_update_time = current_time
                    last_queue_size = current_queue_size
                
                # Short sleep to prevent CPU spinning
                time.sleep(1)
            
            # Wait for all threads to finish
            for t in threads:
                t.join(timeout=5)  # 5 second timeout for joining threads
        
        except KeyboardInterrupt:
            logger.warning("User interrupted processing. Saving progress...")
            self.save_progress()
            logger.info("Progress saved. You can resume later.")
            return
        except Exception as e:
            logger.error(f"Error during processing: {e}")
            self.save_progress()
            logger.info("Progress saved due to error. You can resume later.")
            return
        
        # Index all processed documents
        logger.info("Building search index...")
        self.rebuild_index_from_processed()
        
        logger.info("OCR processing and indexing completed")
        
        # Clean up progress file
        if os.path.exists(self.progress_file):
            try:
                os.remove(self.progress_file)
                logger.info("Removed progress tracking file as all processing completed")
            except:
                pass
    
    def rebuild_index_from_processed(self):
        """Rebuild the search index but only from successfully processed text files"""
        try:
            # Get list of all text files in output directory
            text_files = []
            for root, _, files in os.walk(self.output_dir):
                for file in files:
                    if file.lower().endswith('.txt'):
                        text_files.append(os.path.join(root, file))
            
            logger.info(f"Found {len(text_files)} text files to index")
            
            # Create new index
            if os.path.exists(self.index_dir):
                shutil.rmtree(self.index_dir)
            os.makedirs(self.index_dir, exist_ok=True)
            create_in(self.index_dir, schema)
            
            # Index each text file with memory checks
            for i, text_path in enumerate(text_files):
                if i % 50 == 0:  # Check memory periodically
                    if self.check_memory_usage():
                        logger.warning("Memory high during indexing, pausing for garbage collection")
                        time.sleep(2)
                        gc.collect()
                
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
        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")
            
    def rebuild_index(self):
        """Rebuild the search index from existing text files"""
        logger.info("Rebuilding search index...")
        self.rebuild_index_from_processed()
        
def main():
    parser = argparse.ArgumentParser(description="OCR PDF files and build search index")
    parser.add_argument("--input", "-i", help="Input directory containing PDF files")
    parser.add_argument("--site", "-s", help="Site ID from config (alternative to --input)")
    parser.add_argument("--output", "-o", default="ocr_text", help="Output directory for extracted text")
    parser.add_argument("--index", default="search_index", help="Directory for search index")
    parser.add_argument("--workers", "-w", type=int, default=None, help="Number of parallel OCR workers")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild search index from existing text files")
    parser.add_argument("--memory-limit", "-m", type=int, default=None, help="Maximum memory usage percentage")
    
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
    
    # Use command line args if provided, otherwise use defaults
    workers = args.workers if args.workers is not None else DEFAULT_WORKERS
    memory_limit = args.memory_limit if args.memory_limit is not None else MAX_MEMORY
    
    # Create processor
    processor = PDFOCRProcessor(
        input_dir=input_dir,
        output_dir=args.output,
        index_dir=args.index,
        num_workers=workers,
        max_memory_percent=memory_limit
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