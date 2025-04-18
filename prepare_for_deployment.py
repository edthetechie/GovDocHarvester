#!/usr/bin/env python3
"""
GovDocHarvester - Deployment Preparation Script
Prepares the search index and document mappings for web deployment
"""

import os
import sys
import json
import shutil
import argparse
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def prepare_for_deployment(output_dir="deploy", include_pdfs=False, pdf_dir=None, search_index_dir="search_index", ocr_text_dir="ocr_text"):
    """
    Prepare files for deployment to a hosting service
    
    Args:
        output_dir (str): Directory to save deployment files
        include_pdfs (bool): Whether to include PDF files in deployment
        pdf_dir (str): Directory containing PDF files to include
        search_index_dir (str): Directory containing Whoosh search index
        ocr_text_dir (str): Directory containing OCR text files
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Creating deployment files in {output_dir}")
    
    # Copy search index
    index_output_dir = os.path.join(output_dir, "search_index")
    if os.path.exists(search_index_dir):
        logger.info(f"Copying search index from {search_index_dir} to {index_output_dir}")
        if os.path.exists(index_output_dir):
            shutil.rmtree(index_output_dir)
        shutil.copytree(search_index_dir, index_output_dir)
    else:
        logger.error(f"Search index directory not found: {search_index_dir}")
        return False
    
    # Create PDF mappings (empty if no PDFs included)
    pdf_mappings = {}
    
    if include_pdfs and pdf_dir:
        # Create PDFs directory in output
        pdfs_output_dir = os.path.join(output_dir, "pdfs")
        os.makedirs(pdfs_output_dir, exist_ok=True)
        
        # Find all PDF files
        logger.info(f"Scanning for PDF files in {pdf_dir}")
        pdf_count = 0
        for root, _, files in os.walk(pdf_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_path = os.path.join(root, file)
                    
                    # Copy PDF to output dir
                    output_path = os.path.join(pdfs_output_dir, file)
                    shutil.copy2(pdf_path, output_path)
                    
                    # Add to mappings (using relative path for deployment)
                    pdf_mappings[file] = os.path.join("pdfs", file)
                    pdf_count += 1
        
        logger.info(f"Included {pdf_count} PDF files for deployment")
    
    # Write the PDF mappings file
    mapping_path = os.path.join(output_dir, "pdf_mappings.json")
    with open(mapping_path, 'w') as f:
        json.dump(pdf_mappings, f)
    
    logger.info(f"Created PDF mappings file with {len(pdf_mappings)} entries")
    
    # Copy template directory if it exists
    template_dir = "templates"
    if os.path.exists(template_dir):
        templates_output_dir = os.path.join(output_dir, "templates")
        logger.info(f"Copying templates from {template_dir} to {templates_output_dir}")
        if os.path.exists(templates_output_dir):
            shutil.rmtree(templates_output_dir)
        shutil.copytree(template_dir, templates_output_dir)
    
    # Copy static directory if it exists
    static_dir = "static"
    if os.path.exists(static_dir):
        static_output_dir = os.path.join(output_dir, "static")
        logger.info(f"Copying static files from {static_dir} to {static_output_dir}")
        if os.path.exists(static_output_dir):
            shutil.rmtree(static_output_dir)
        shutil.copytree(static_dir, static_output_dir)
    
    # Copy web app files
    for file in ["web_app.py", "Procfile", "requirements_web.txt"]:
        if os.path.exists(file):
            logger.info(f"Copying {file} to deployment directory")
            shutil.copy2(file, os.path.join(output_dir, file))
    
    # Rename requirements_web.txt to requirements.txt for platforms that expect it
    shutil.copy2(os.path.join(output_dir, "requirements_web.txt"), 
                os.path.join(output_dir, "requirements.txt"))
    
    # Create a simple README.md file
    with open(os.path.join(output_dir, "README.md"), 'w') as f:
        f.write("""# GovDocHarvester - Web Search Interface

This is the web search interface for the GovDocHarvester project. It allows users to search through OCR'd government documents.

## Deployment

This application is ready for deployment on platforms like Render, Railway, or Heroku.

## File Structure

- `web_app.py` - The main Flask application
- `search_index/` - The Whoosh search index
- `templates/` - HTML templates
- `pdfs/` - PDF documents (if included)
- `pdf_mappings.json` - Mapping of document filenames to paths
- `requirements.txt` - Python package dependencies
""")
    
    logger.info(f"Deployment preparation complete. Files ready in {output_dir}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Prepare GovDocHarvester for web deployment")
    parser.add_argument("--output", default="deploy", help="Output directory for deployment files")
    parser.add_argument("--include-pdfs", action="store_true", help="Include PDF files in deployment")
    parser.add_argument("--pdf-dir", help="Directory containing PDF files (required if --include-pdfs is used)")
    parser.add_argument("--search-index", default="search_index", help="Directory containing search index")
    
    args = parser.parse_args()
    
    if args.include_pdfs and not args.pdf_dir:
        parser.error("--pdf-dir is required when --include-pdfs is set")
    
    if args.include_pdfs and args.pdf_dir:
        if not os.path.exists(args.pdf_dir):
            parser.error(f"PDF directory not found: {args.pdf_dir}")
    
    prepare_for_deployment(
        output_dir=args.output,
        include_pdfs=args.include_pdfs,
        pdf_dir=args.pdf_dir,
        search_index_dir=args.search_index
    )

if __name__ == "__main__":
    main()