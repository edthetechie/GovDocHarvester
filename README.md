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

### Step 3: Search Documents
Launch the web search interface:
```
python run_pdf_search.py --search
```

Access the search interface in your browser:
```
http://127.0.0.1:5000
```

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

## 🗂️ Project Structure
- `pdf_downloader.py`: Core PDF downloading functionality
- `download_site.py`: Simplified interface for pre-configured sites
- `ocr_processor.py`: OCR processing for scanned PDFs
- `search_app.py`: Web-based search interface
- `run_pdf_search.py`: Combined control script 
- `check_ocr_setup.py`: Diagnostic tool for OCR setup

## 📚 Use Cases
- Research: Access and analyze historical government documents
- Journalism: Investigate government records databases
- Archiving: Create local searchable copies of important collections
- Legal: Build document collections for legal discovery

## ⚠️ Important Notes
- Always be considerate when crawling websites and respect their `robots.txt` files
- Large PDF collections may require significant disk space and processing time
- OCR quality depends on the quality of the original scans

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