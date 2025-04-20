# GovDocHarvester 📚

![Python](https://img.shields.io/badge/python-3.6+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

A comprehensive Python toolkit for downloading, processing, and searching government document collections. Originally designed for the Robert F. Kennedy Assassination Archives, but flexible enough for any document repository.

<p align="center">
  <img src="https://raw.githubusercontent.com/python/pythondotorg/main/static/img/python-logo.png" alt="Python Logo" width="200"/>
</p>

## ✨ Features

### 📥 Document Collection
- Intelligently crawls websites to find and download all PDF files
- Configurable crawl depth and request delays to be respectful to servers
- Pre-configured for common U.S. government document collections
- Easy to add new website configurations through `config.py`
- Progress bars and detailed logging
- Automatically skips already downloaded files

### 🔍 OCR Processing & Search
- Convert scanned PDFs to searchable text using Tesseract OCR
- Memory-efficient processing that prevents system crashes
- Multi-threaded OCR for faster processing
- Resume capability for interrupted OCR jobs
- Web-based search interface to find documents
- Full-text search with highlighted results
- Direct PDF viewing from search results

### 🔗 Archive.gov Integration
- Dynamic mapping between local files and their original archives.gov URLs
- Automatic URL mapping during download process
- Verification tools to ensure archive links are valid
- Pattern-based document identification that works even with partial filenames
- Automatic redirection to archives.gov when local PDFs aren't available
- Support for different document collections (FBI files, State Department files, etc.)

## 🛠️ Installation

### Prerequisites
- Python 3.6+
- Tesseract OCR ([Windows](https://github.com/UB-Mannheim/tesseract/wiki), [macOS](https://brew.sh/), [Linux](https://github.com/tesseract-ocr/tesseract))
- Poppler ([Windows](https://github.com/oschwartz10612/poppler-windows/releases/), [macOS](https://brew.sh/), [Linux](https://poppler.freedesktop.org/))

### Setup
1. Clone this repository:
   ```
   git clone https://github.com/yourusername/govdocharvester.git
   cd govdocharvester
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   pip install -r requirements_ocr.txt
   ```

3. Configure Tesseract and Poppler paths in `ocr_config.py`:
   ```python
   TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Update for your system
   POPPLER_PATH = r"C:\Program Files\poppler\bin"  # Update for your system
   ```

## 📋 Usage

### Step 1: Download PDF Documents
List available pre-configured websites:
```
python download_site.py --list
```

Download PDFs from a specific collection:
```
python download_site.py rfk
```

Override the crawl depth or delay:
```
python download_site.py rfk --depth 4 --delay 2
```

Custom URL download:
```
python pdf_downloader.py https://www.archives.gov/research/rfk -o downloads/custom -d 3 --delay 1.0
```

### Step 2: Process Documents with OCR
First, verify your OCR setup:
```
python check_ocr_setup.py
```

Process PDFs with memory-efficient OCR (recommended):
```
run_ocr.bat --ocr rfk
```

Or manually with Python:
```
python run_pdf_search.py --ocr rfk --memory-limit 75 --workers 2
```

### Step 3: Archive URL Mapping
The system now automatically creates mappings between your PDFs and archives.gov URLs during the download process. However, you can also:

Verify existing archive links:
```
python run_pdf_search.py --verify-links
```

Regenerate mappings if needed:
```
python run_pdf_search.py --generate-mappings
```

Find actual PDF files on archives.gov and map them to local files:
```
python find_archive_pdfs.py
```

### Step 4: Search Documents
Launch the web search interface:
```
python web_app.py
```

Access the search interface in your browser:
```
http://127.0.0.1:5000
```

Now you can search through documents, and if a local PDF is not available, users will be redirected to the corresponding archives.gov page.

## 📝 Advanced Configuration

### Adding New Document Collections
Edit the `config.py` file and add a new entry to the `WEBSITE_CONFIGS` dictionary:

```python
"new_site_id": {
    "url": "https://www.example.gov/documents",
    "description": "Description of the document collection",
    "output_dir": "downloads/new_site_id",
    "depth": 3,
    "delay": 1.0
}
```

### OCR Configuration Options
Edit the `ocr_config.py` file to adjust:
- `OCR_WORKERS`: Number of parallel processing threads
- `MAX_MEMORY_PERCENT`: Memory threshold to prevent crashes

### Archive URL Mapping Configuration
Archive URL mappings are now generated automatically during download, but you can customize:
- Domain settings via `--domain` parameter when downloading or regenerating mappings
- Manual mappings by editing the `archive_mappings.json` file directly

## 🗂️ Project Structure
- `pdf_downloader.py`: Core PDF downloading functionality with automatic URL mapping
- `download_site.py`: Simplified interface for pre-configured sites
- `ocr_processor.py`: OCR processing for scanned PDFs
- `search_app.py`: Search index creation and querying
- `web_app.py`: Web-based search and document viewing interface
- `archive_mappings.py`: URL mapping utility functions
- `find_archive_pdfs.py`: Tool to locate actual PDFs on archives.gov 
- `run_pdf_search.py`: Combined control script with mapping validation
- `check_ocr_setup.py`: Diagnostic tool for OCR setup

## 📚 Use Cases
- Research: Access and analyze historical government documents
- Journalism: Investigate government records databases
- Archiving: Create local searchable copies of important collections
- Legal: Build document collections for legal discovery
- Education: Provide access to primary source materials for students

## ⚠️ Important Notes
- Always be considerate when crawling websites and respect their `robots.txt` files
- Large PDF collections may require significant disk space and processing time
- OCR quality depends on the quality of the original scans
- Make sure to use "archives.gov" (with an 's') as the domain for National Archives links

## 🚀 Deployment
This project is ready for cloud deployment:
- `Procfile` and `render.yaml` for easy deployment to Heroku or Render
- `prepare_for_deployment.py` script to optimize for cloud environments
- Separate requirements files for minimal production deployments

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments
- Built with GitHub Copilot
- Special thanks to the [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) project
- Uses [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) for HTML parsing
- Search powered by [Whoosh](https://whoosh.readthedocs.io/)
- Web interface built with [Flask](https://flask.palletsprojects.com/)

---
<p align="center">
<i>Empowering transparency through accessible public documents</i>
</p>