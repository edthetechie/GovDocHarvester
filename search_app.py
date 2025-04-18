#!/usr/bin/env python3
"""
PDF Search Web Interface - Search through OCR'd PDF documents
"""

import os
import sys
import argparse
from flask import Flask, render_template, request, redirect, url_for, send_file
from whoosh.index import open_dir
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.highlight import ContextFragmenter
from config import WEBSITE_CONFIGS
import logging

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

app = Flask(__name__)

class PDFSearchApp:
    def __init__(self, index_dir="search_index", pdf_dirs=None):
        """
        Initialize the search application
        
        Args:
            index_dir (str): Directory containing the search index
            pdf_dirs (list): List of directories containing PDF files
        """
        self.index_dir = index_dir
        self.pdf_dirs = pdf_dirs or []
        
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
        """
        Search the index for documents matching the query
        
        Args:
            query_text (str): Search query
            page (int): Page number for pagination
            per_page (int): Results per page
        
        Returns:
            dict: Search results
        """
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
                    
                    formatted_results.append({
                        "title": title,
                        "path": pdf_path,
                        "filename": hit["filename"],
                        "snippets": snippets,
                        "score": hit.score,
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
    
    def find_pdf(self, filename):
        """
        Find the actual path to a PDF file
        
        Args:
            filename (str): Filename of the PDF
        
        Returns:
            str: Full path to the PDF file
        """
        # First look in the specified PDF directories
        for pdf_dir in self.pdf_dirs:
            pdf_path = os.path.join(pdf_dir, filename)
            if os.path.exists(pdf_path):
                return pdf_path
        
        # If not found, try to find it in all website config directories
        for site_id, config in WEBSITE_CONFIGS.items():
            pdf_dir = config.get("output_dir")
            if pdf_dir:
                pdf_path = os.path.join(pdf_dir, filename)
                if os.path.exists(pdf_path):
                    return pdf_path
        
        # If still not found, return None
        return None

# Initialize the search app
search_app = None

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
    """View a PDF file"""
    pdf_path = search_app.find_pdf(filename)
    
    if pdf_path and os.path.exists(pdf_path):
        try:
            return send_file(pdf_path, download_name=filename)
        except Exception as e:
            logger.error(f"Error sending PDF file: {e}")
            return f"Error: Could not retrieve the PDF file. {str(e)}", 500
    else:
        return "PDF file not found", 404

def create_app(index_dir="search_index", pdf_dirs=None):
    """Create the Flask application with the search app"""
    global search_app
    search_app = PDFSearchApp(index_dir=index_dir, pdf_dirs=pdf_dirs or [])
    
    # Create templates directory if it doesn't exist
    os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)
    
    # Create basic templates
    create_templates()
    
    return app

def create_templates():
    """Create basic HTML templates for the search app"""
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    
    # Home page template
    with open(os.path.join(templates_dir, 'search.html'), 'w') as f:
        f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>PDF Search</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }
        .search-container {
            text-align: center;
            margin-top: 100px;
        }
        .search-box {
            width: 80%;
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .search-button {
            padding: 10px 20px;
            background-color: #4285f4;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        h1 {
            color: #333;
        }
        footer {
            margin-top: 50px;
            text-align: center;
            color: #777;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="search-container">
        <h1>PDF Document Search</h1>
        <p>Search through OCR'd PDF documents</p>
        <form action="/search" method="get">
            <input type="text" name="q" class="search-box" placeholder="Enter search terms...">
            <button type="submit" class="search-button">Search</button>
        </form>
    </div>
    <footer>
        <p>Powered by Python, Flask, Tesseract OCR and Whoosh</p>
    </footer>
</body>
</html>
''')
    
    # Search results template
    with open(os.path.join(templates_dir, 'results.html'), 'w') as f:
        f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Search Results for "{{ query }}"</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }
        .search-container {
            margin-bottom: 20px;
        }
        .search-box {
            width: 60%;
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .search-button {
            padding: 10px 20px;
            background-color: #4285f4;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        .result {
            margin-bottom: 30px;
            padding: 15px;
            border-bottom: 1px solid #eee;
        }
        .result-title {
            font-size: 18px;
            margin-bottom: 5px;
        }
        .result-title a {
            color: #1a0dab;
            text-decoration: none;
        }
        .result-title a:hover {
            text-decoration: underline;
        }
        .result-snippet {
            color: #333;
            line-height: 1.5;
        }
        .highlight {
            background-color: #ffffcc;
            font-weight: bold;
        }
        .pagination {
            margin-top: 30px;
            text-align: center;
        }
        .pagination a {
            display: inline-block;
            padding: 8px 16px;
            text-decoration: none;
            color: #1a0dab;
            margin: 0 5px;
        }
        .pagination a.active {
            background-color: #4285f4;
            color: white;
        }
        .pagination a:hover:not(.active) {
            background-color: #ddd;
        }
        .result-info {
            margin-bottom: 20px;
            color: #777;
        }
        .home-link {
            margin-bottom: 20px;
        }
        .home-link a {
            color: #1a0dab;
            text-decoration: none;
        }
        .home-link a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="home-link">
        <a href="/">&larr; Back to Home</a>
    </div>
    <div class="search-container">
        <form action="/search" method="get">
            <input type="text" name="q" class="search-box" value="{{ query }}">
            <button type="submit" class="search-button">Search</button>
        </form>
    </div>
    
    <div class="result-info">
        Found {{ total }} results for <strong>{{ query }}</strong>
    </div>
    
    {% if results %}
        {% for result in results %}
            <div class="result">
                <div class="result-title">
                    <a href="{{ url_for('view_pdf', filename=result.filename) }}" target="_blank">
                        {{ result.title }}
                    </a>
                </div>
                <div class="result-snippet">
                    {{ result.snippets|safe }}
                </div>
            </div>
        {% endfor %}
        
        <div class="pagination">
            {% if has_previous %}
                <a href="{{ url_for('search', q=query, page=page-1) }}">&laquo; Previous</a>
            {% endif %}
            
            <span>Page {{ page }} of {{ pages }}</span>
            
            {% if has_next %}
                <a href="{{ url_for('search', q=query, page=page+1) }}">Next &raquo;</a>
            {% endif %}
        </div>
    {% else %}
        <p>No results found for your query. Please try different search terms.</p>
    {% endif %}
</body>
</html>
''')

def main():
    parser = argparse.ArgumentParser(description="Start the PDF search web interface")
    parser.add_argument("--index", default="search_index", help="Directory containing the search index")
    parser.add_argument("--pdf-dir", action='append', help="Directory containing PDF files (can be used multiple times)")
    parser.add_argument("--host", default="127.0.0.1", help="Host to run the web server on")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the web server on")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    
    args = parser.parse_args()
    
    # Ensure index directory exists
    if not os.path.exists(args.index):
        print(f"Error: Search index directory not found: {args.index}")
        print("Please run the OCR processor first to create the search index.")
        return 1
    
    # Check for PDF directories
    pdf_dirs = args.pdf_dir or []
    if not pdf_dirs:
        # If no PDF directories specified, use all from config
        for site_id, config in WEBSITE_CONFIGS.items():
            pdf_dir = config.get("output_dir")
            if pdf_dir and os.path.exists(pdf_dir):
                pdf_dirs.append(pdf_dir)
    
    # Create and run the app
    app = create_app(index_dir=args.index, pdf_dirs=pdf_dirs)
    print(f"* PDF Search web interface started at http://{args.host}:{args.port}")
    print(f"* Using search index: {args.index}")
    print(f"* PDF directories: {', '.join(pdf_dirs)}")
    app.run(host=args.host, port=args.port, debug=args.debug)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())