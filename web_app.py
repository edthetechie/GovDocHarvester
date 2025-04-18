#!/usr/bin/env python3
"""
GovDocHarvester - Web Search Interface
Simplified version for deployment to cloud platforms
"""

import os
import sys
from flask import Flask, render_template, request, redirect, url_for, send_file
from whoosh.index import open_dir
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.highlight import ContextFragmenter
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='static')

# Load PDF path mappings
PDF_PATHS = {}
try:
    if os.path.exists('pdf_mappings.json'):
        with open('pdf_mappings.json', 'r') as f:
            PDF_PATHS = json.load(f)
except Exception as e:
    logger.error(f"Error loading PDF mappings: {e}")

class PDFSearchApp:
    def __init__(self, index_dir="search_index"):
        """Initialize the search application"""
        self.index_dir = index_dir
        
        try:
            # Open the search index
            if os.path.exists(index_dir):
                self.ix = open_dir(index_dir)
                logger.info(f"Search index opened from {index_dir}")
            else:
                logger.error(f"Search index directory not found: {index_dir}")
                self.ix = None
        except Exception as e:
            logger.error(f"Failed to open search index: {e}")
            self.ix = None
    
    def search(self, query_text, page=1, per_page=10):
        """Search the index for documents matching the query"""
        if not self.ix:
            logger.error("Search index not available")
            return {"query": query_text, "total": 0, "results": [], "page": page, "pages": 0}
        
        try:
            # Calculate offset for pagination
            start_offset = (page - 1) * per_page
            
            with self.ix.searcher() as searcher:
                # Create a parser that searches both title and content
                parser = MultifieldParser(["title", "content"], self.ix.schema)
                query = parser.parse(query_text)
                
                # Create a context fragmenter for better highlighting
                fragmenter = ContextFragmenter(maxchars=300, surround=50)
                
                # Execute the search
                results = searcher.search_page(query, page, pagelen=per_page)
                results.fragmenter = fragmenter
                
                # Format results
                formatted_results = []
                for hit in results:
                    # Create highlighted snippets from the content field
                    snippets = hit.highlights("content", top=3) or "No preview available"
                    
                    # Find the PDF file
                    pdf_path = hit["path"]
                    title = hit["title"]
                    filename = hit["filename"]
                    
                    # Check if this file is available in the PDF mappings
                    has_pdf = filename in PDF_PATHS
                    
                    formatted_results.append({
                        "title": title,
                        "path": pdf_path,
                        "filename": filename,
                        "snippets": snippets,
                        "score": hit.score,
                        "has_pdf": has_pdf
                    })
                
                # Return search results and pagination info
                return {
                    "query": query_text,
                    "total": len(results),
                    "total_docs": results.total,
                    "results": formatted_results,
                    "page": page,
                    "pages": results.pagecount,
                    "has_previous": results.pagenum > 1,
                    "has_next": results.pagenum < results.pagecount
                }
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {"query": query_text, "total": 0, "results": [], "page": page, "pages": 0}

# Initialize the search app
search_app = PDFSearchApp()

@app.route('/')
def home():
    """Home page with search form"""
    return render_template('search.html')

@app.route('/search')
def search():
    """Handle search requests"""
    query = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    
    if not query:
        return redirect(url_for('home'))
    
    # Perform the search
    results = search_app.search(query, page=page)
    
    return render_template(
        'results.html',
        query=query,
        results=results["results"],
        total=results["total_docs"],
        page=results["page"],
        pages=results["pages"],
        has_previous=results["has_previous"],
        has_next=results["has_next"]
    )

@app.route('/view/<path:filename>')
def view_pdf(filename):
    """View a PDF file if available"""
    if filename in PDF_PATHS:
        try:
            return send_file(PDF_PATHS[filename], download_name=filename)
        except Exception as e:
            logger.error(f"Error sending PDF file: {e}")
            return f"Error: Could not retrieve the PDF file. {str(e)}", 500
    else:
        return render_template('pdf_unavailable.html', filename=filename)

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

# Create an error handler for 404 errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == "__main__":
    # Use PORT environment variable for cloud platforms
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)