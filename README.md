# Website PDF Downloader

A Python application designed to download PDF files from government websites with easy configuration for different sites.

## Features

- Crawls websites to find and download all PDF files
- Configurable crawl depth and request delays to be respectful to servers
- Pre-configured for common U.S. government document collections
- Easy to add new website configurations
- Progress bars for downloads with detailed logging
- Skips already downloaded files

## Installation

1. Clone or download this repository
2. Install the required dependencies:

```
pip install -r requirements.txt
```

## Usage

### Option 1: Use the simplified script with pre-configured websites

List available website configurations:
```
python download_site.py --list
```

Download PDFs from a specific site:
```
python download_site.py rfk
```

Override the crawl depth or delay:
```
python download_site.py rfk --depth 4 --delay 2
```

### Option 2: Use the generic downloader with any URL

```
python pdf_downloader.py https://www.archives.gov/research/rfk -o downloads/rfk -d 3 --delay 1.0
```

## Adding New Website Configurations

To add new website configurations, edit the `config.py` file and add a new entry to the `WEBSITE_CONFIGS` dictionary:

```python
"new_site_id": {
    "url": "https://www.example.gov/documents",
    "description": "Description of the document collection",
    "output_dir": "downloads/new_site_id",
    "depth": 3,
    "delay": 1.0
}
```

## Configuration Options

- `url`: The base URL to start crawling from
- `description`: A description of the website/collection
- `output_dir`: Directory where PDFs will be saved
- `depth`: How many levels of links to follow from the base URL
- `delay`: Time to wait between requests (in seconds) to avoid overloading the server