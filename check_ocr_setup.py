#!/usr/bin/env python3
"""
OCR Setup Checker - Test if OCR dependencies are correctly installed
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
import pkg_resources

def check_python_packages():
    """Check if required Python packages are installed"""
    required_packages = ['pytesseract', 'pdf2image', 'whoosh', 'flask']
    missing_packages = []
    
    installed_packages = {pkg.key for pkg in pkg_resources.working_set}
    
    for package in required_packages:
        try:
            __import__(package.lower())
            print(f"✓ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} is NOT installed")
    
    # Special check for PIL/Pillow
    try:
        # The proper way to import Pillow is through specific modules
        from PIL import Image
        print(f"✓ PIL (Pillow) is installed")
    except ImportError:
        missing_packages.append('pillow')
        print(f"✗ PIL is NOT installed")
    
    if missing_packages:
        print("\nSome packages are missing. Install them with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_tesseract():
    """Check if Tesseract OCR is installed and accessible"""
    print("Checking Tesseract installation details...")
    
    # First, check if we can import pytesseract
    try:
        import pytesseract
        print(f"  - pytesseract module imported successfully")
        print(f"  - Current tesseract_cmd path: {pytesseract.pytesseract.tesseract_cmd}")
    except Exception as e:
        print(f"  - Failed to import pytesseract: {e}")
    
    # Try to load from our config file
    try:
        from ocr_config import TESSERACT_PATH
        print(f"  - Found path in ocr_config.py: {TESSERACT_PATH}")
        
        if os.path.exists(TESSERACT_PATH):
            print(f"  - The file exists at the path")
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
            print(f"  - Set tesseract path to: {pytesseract.pytesseract.tesseract_cmd}")
        else:
            print(f"  - WARNING: The file does NOT exist at {TESSERACT_PATH}")
    except ImportError:
        print("  - Could not import TESSERACT_PATH from ocr_config.py")
    except Exception as e:
        print(f"  - Error when setting up Tesseract path: {e}")
    
    # Now try to get the version
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✓ Tesseract OCR is installed (version {version})")
        return True
    except Exception as e:
        print("✗ Tesseract OCR is NOT properly configured")
        print(f"  Error: {str(e)}")
        
        # Check if tesseract is directly callable from command line
        try:
            result = subprocess.run(['tesseract', '--version'], 
                                   capture_output=True, text=True, check=True)
            print("  Tesseract is in PATH but Python can't access it")
            print("  Command line output:")
            print(f"  {result.stdout[:200]}...")
        except FileNotFoundError:
            print("\nTesseract is not in system PATH.")
            
            # Check common installation locations
            common_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Tesseract-OCR', 'tesseract.exe')
            ]
            
            for path in common_paths:
                if os.path.exists(path):
                    print(f"  Found Tesseract at: {path}")
                    print(f"  Try manually setting: pytesseract.pytesseract.tesseract_cmd = r'{path}'")
        except Exception as e:
            print(f"\n  Error checking Tesseract command: {e}")
        
        return False

def check_poppler():
    """Check if Poppler is installed and accessible"""
    try:
        from pdf2image import convert_from_path
        
        # Create a simple test PDF
        test_pdf_path = os.path.join(tempfile.gettempdir(), "test_poppler.pdf")
        with open(test_pdf_path, 'w') as f:
            f.write("%PDF-1.7\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%EOF")
        
        # Try to convert the PDF to image
        images = convert_from_path(test_pdf_path, dpi=72)
        os.unlink(test_pdf_path)
        
        print("✓ Poppler is installed and working correctly")
        return True
    except Exception as e:
        print("✗ Poppler is NOT properly configured")
        print(f"  Error: {str(e)}")
        print("\nTo install Poppler on Windows:")
        print("1. Download from: https://github.com/oschwartz10612/poppler-windows/releases/")
        print("2. Extract the ZIP file to a folder (e.g., C:\\Program Files\\poppler)")
        print("3. Add the bin folder to your PATH (e.g., C:\\Program Files\\poppler\\bin)")
        return False

def fix_poppler_path():
    """Try to find Poppler in common installation directories and add to PATH"""
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
            # Add to PATH for this session
            os.environ['PATH'] = poppler_path + os.pathsep + os.environ['PATH']
            print(f"\nFound Poppler in {poppler_path}")
            print("Added to PATH for this session")
            return True
    
    return False

def test_simple_ocr():
    """Test OCR on a simple image if all dependencies are available"""
    if not check_tesseract() or not check_poppler():
        return False
    
    try:
        # Correct import from PIL
        from PIL import Image, ImageDraw
        import pytesseract
        
        # Create a simple test image with text
        img = Image.new('RGB', (200, 50), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((10, 10), "Hello, OCR!", fill=(0, 0, 0))
        
        test_img_path = os.path.join(tempfile.gettempdir(), "test_ocr.png")
        img.save(test_img_path)
        
        # Run OCR on the image
        text = pytesseract.image_to_string(Image.open(test_img_path))
        os.unlink(test_img_path)
        
        if "Hello" in text:
            print("\n✓ OCR test successful!")
            print(f"  Text detected: {text.strip()}")
            return True
        else:
            print("\n✗ OCR test failed to detect correct text")
            print(f"  Text detected: {text.strip()}")
            return False
            
    except Exception as e:
        print("\n✗ OCR test failed with error:")
        print(f"  {str(e)}")
        return False

def main():
    print("=" * 60)
    print("OCR Setup Checker - Testing your OCR dependencies")
    print("=" * 60)
    
    print("\nChecking Python packages:")
    packages_ok = check_python_packages()
    
    print("\nChecking Tesseract OCR installation:")
    tesseract_ok = check_tesseract()
    
    print("\nChecking Poppler installation:")
    poppler_ok = check_poppler()
    
    if not poppler_ok:
        print("\nTrying to find Poppler in common locations...")
        if fix_poppler_path():
            print("Checking Poppler installation again:")
            poppler_ok = check_poppler()
    
    print("\n" + "=" * 60)
    if tesseract_ok and poppler_ok and packages_ok:
        print("All OCR dependencies are properly installed!")
        print("\nTesting OCR functionality:")
        test_simple_ocr()
        print("\nYou should be able to run OCR processing on your PDFs now:")
        print("python run_pdf_search.py --ocr rfk")
    else:
        print("Some OCR dependencies are missing or not configured correctly.")
        print("Please fix the issues above before running OCR processing.")
    print("=" * 60)

if __name__ == "__main__":
    main()