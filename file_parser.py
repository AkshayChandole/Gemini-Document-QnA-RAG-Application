from abc import ABC, abstractmethod
import logging
import pytesseract
from PIL import Image # pillow
import fitz  # PyMuPDF
import io
import PyPDF2
import os
from typing import Type, Dict

# Configure Tesseract path for Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class BaseParser(ABC):
    """Abstract base class for file parsers."""

    @abstractmethod
    def parse(self, file_path: str):
        """Abstract method to parse file content."""
        pass
    
class TextParser(BaseParser):
    """Concrete Parser for TXT files."""

    def parse(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            return content
        except Exception as e:
            logging.error(f"Error reading text file {file_path}: {e}")
            return "Error reading text file."

class PDFParser(BaseParser):
    """Concrete Parser for PDF files"""

    def parse(self, file_path: str) -> str:
        try:
            content = ""
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                if reader.is_encrypted:
                    try:
                        reader.decrypt('')
                    except Exception as e:
                        logging.error(f"Failed to decrypt PDF file {file_path}: {e}")
                        return "Unable to decrypt PDF file."
                
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    page_content = page.extract_text()
                    if not page_content: # If text extraction fails, use OCR
                        page_content = self._ocr_page(file_path, page_num)
                    content += page_content + "\n"       
            return content
        except Exception as e:
            logging.error(f"Error reading PDF file {file_path}: {e}")
            return "Error reading PDF file."
        
    def _ocr_page(self, file_path: str, page_num: int) -> str:
        """Perform OCR on a specific page of the PDF."""
        try:
            doc = fitz.open(file_path)
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            ocr_text = pytesseract.image_to_string(img)
            return ocr_text
        except Exception as e:
            logging.error(f"OCR processing error: {e}")
            return "Error during OCR processing."
        
class ParserFactory:
    """Factory class to get the appropriate parser based on file extension."""

    _parsers: Dict[str, Type[BaseParser]] = {}
    
    @classmethod
    def register_parser(cls, extension: str, parser: Type[BaseParser]) -> None:
        cls._parsers[extension.lower()] = parser

    @classmethod
    def get_parser(cls, file_extension: str) -> BaseParser:
        _parser = cls._parsers.get(file_extension.lower())
        if not _parser:
            raise ValueError(f"No parser available for the .{file_extension} file type.")
        return _parser()

ParserFactory.register_parser("txt", TextParser)
ParserFactory.register_parser("pdf", PDFParser)


class FileParser:
    """Class to handle file parsing using the appropriate parser."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.parser = self._get_parser()
    
    def _get_parser(self) -> BaseParser:
        extension = self.file_path.split('.')[-1]
        if extension not in ParserFactory._parsers:
            raise ValueError(f"Unsupported file extension: .{extension}")
        return ParserFactory.get_parser(extension)
    
    def parse(self) -> str:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")
        return self.parser.parse(self.file_path)