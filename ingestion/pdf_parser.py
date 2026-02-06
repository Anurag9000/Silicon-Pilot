"""
PDF Parser

Multi-strategy PDF parsing with layout-aware table extraction,
OCR fallback, and bounding box capture for evidence.
"""

import logging
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
import tempfile
import fitz  # PyMuPDF
import pdfplumber
import camelot
import pytesseract
from PIL import Image
import io

logger = logging.getLogger(__name__)


class PDFParser:
    """Parse PDFs with multiple strategies for robustness"""
    
    def __init__(self, tesseract_cmd: Optional[str] = None):
        """
        Initialize PDF parser.
        
        Args:
            tesseract_cmd: Path to tesseract executable (None for system default)
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    
    def parse(self, input_data: Any) -> Dict:
        """
        Parse PDF with all available strategies.
        
        Args:
            input_data: PDF file content (bytes) or path to PDF (str)
        
        Returns:
            Dict with pages, tables, and metadata
        """
        logger.info("Parsing PDF")
        
        temp_file = None
        if isinstance(input_data, str):
            pdf_path = input_data
            pdf_bytes = Path(pdf_path).read_bytes()
        else:
            pdf_bytes = input_data
            # Save to temp file for Camelot (which requires a path)
            temp_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False)
            temp_file.write(pdf_bytes)
            temp_file.close()
            pdf_path = temp_file.name
        
        result = {
            'pages': [],
            'tables': [],
            'metadata': {},
        }
        
        try:
            # Extract metadata and pages
            result['metadata'], result['pages'] = self._extract_pages(pdf_bytes)
            
            # Extract tables
            result['tables'] = self._extract_tables(pdf_path)
            
        finally:
            # Cleanup temp file if we created one
            if temp_file is not None:
                try:
                    Path(temp_file.name).unlink()
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file: {e}")
        
        return result
    
    def _extract_pages(self, pdf_bytes: bytes) -> Tuple[Dict, List[Dict]]:
        """
        Extract page-level data using PyMuPDF and pdfplumber.
        
        Returns:
            Tuple of (metadata, pages)
        """
        pages = []
        metadata = {}
        
        # PyMuPDF for rendering and metadata
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        metadata = pdf_doc.metadata
        
        # pdfplumber for text extraction
        pdf_plumber = pdfplumber.open(io.BytesIO(pdf_bytes))
        
        for page_num in range(len(pdf_doc)):
            pymupdf_page = pdf_doc[page_num]
            plumber_page = pdf_plumber.pages[page_num]
            
            page_data = {
                'page_number': page_num + 1,
                'width': pymupdf_page.rect.width,
                'height': pymupdf_page.rect.height,
                'text': plumber_page.extract_text() or "",
                'text_density': self._calculate_text_density(plumber_page),
                'blocks': [],
            }
            
            # Extract text blocks with bounding boxes (for evidence)
            blocks = pymupdf_page.get_text("dict")["blocks"]
            for block in blocks:
                if block.get('type') == 0:  # Text block
                    page_data['blocks'].append({
                        'bbox': block['bbox'],  # (x0, y0, x1, y1)
                        'text': ' '.join([
                            span['text']
                            for line in block.get('lines', [])
                            for span in line.get('spans', [])
                        ]),
                    })
            
            # Check if page needs OCR (low text density)
            if page_data['text_density'] < 0.1:
                logger.info(f"Page {page_num + 1} has low text density, applying OCR")
                ocr_text = self._ocr_page(pymupdf_page)
                page_data['text'] = ocr_text
                page_data['ocr_applied'] = True
            else:
                page_data['ocr_applied'] = False
            
            pages.append(page_data)
        
        pdf_doc.close()
        pdf_plumber.close()
        
        return metadata, pages
    
    def _calculate_text_density(self, page) -> float:
        """
        Calculate text density of a page (text area / total area).
        Low density indicates image-based content.
        """
        try:
            text = page.extract_text()
            if not text:
                return 0.0
            
            # Rough heuristic: characters per square inch
            char_count = len(text.strip())
            page_area = page.width * page.height
            
            # Normalize to 0-1 range (assume 500 chars per page is "normal")
            density = min(char_count / 500.0, 1.0)
            return density
        except Exception:
            return 0.0
    
    def _ocr_page(self, page) -> str:
        """Apply OCR to a page using Tesseract"""
        try:
            # Render page to image
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            
            # Apply OCR
            text = pytesseract.image_to_string(img)
            return text
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""
    
    def _extract_tables(self, pdf_path: str) -> List[Dict]:
        """
        Extract tables using Camelot.
        
        Returns:
            List of tables with page numbers and data
        """
        tables = []
        
        try:
            # Try lattice mode first (for bordered tables)
            lattice_tables = camelot.read_pdf(
                pdf_path,
                pages='all',
                flavor='lattice',
                suppress_stdout=True,
            )
            
            for table in lattice_tables:
                tables.append({
                    'page': table.page,
                    'data': table.df.to_dict('records'),
                    'raw_data': table.data,
                    'bbox': table._bbox,
                    'accuracy': table.accuracy,
                    'method': 'lattice',
                })
            
            # Try stream mode for borderless tables
            stream_tables = camelot.read_pdf(
                pdf_path,
                pages='all',
                flavor='stream',
                suppress_stdout=True,
            )
            
            for table in stream_tables:
                # Avoid duplicates (check if bbox overlaps with lattice tables)
                if not self._is_duplicate_table(table, tables):
                    tables.append({
                        'page': table.page,
                        'data': table.df.to_dict('records'),
                        'raw_data': table.data,
                        'bbox': table._bbox,
                        'accuracy': table.accuracy,
                        'method': 'stream',
                    })
            
            logger.info(f"Extracted {len(tables)} tables")
        
        except Exception as e:
            logger.error(f"Table extraction failed: {e}")
        
        return tables
    
    def _is_duplicate_table(self, table, existing_tables: List[Dict]) -> bool:
        """Check if table overlaps with existing tables on same page"""
        for existing in existing_tables:
            if existing['page'] == table.page:
                # Check bbox overlap (simple heuristic)
                bbox1 = table._bbox
                bbox2 = existing['bbox']
                
                # If bboxes overlap significantly, consider duplicate
                overlap = self._bbox_overlap(bbox1, bbox2)
                if overlap > 0.5:
                    return True
        
        return False
    
    def _bbox_overlap(self, bbox1, bbox2) -> float:
        """Calculate overlap ratio between two bounding boxes"""
        try:
            x1_min, y1_min, x1_max, y1_max = bbox1
            x2_min, y2_min, x2_max, y2_max = bbox2
            
            # Calculate intersection
            x_overlap = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
            y_overlap = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
            intersection = x_overlap * y_overlap
            
            # Calculate union
            area1 = (x1_max - x1_min) * (y1_max - y1_min)
            area2 = (x2_max - x2_min) * (y2_max - y2_min)
            union = area1 + area2 - intersection
            
            return intersection / union if union > 0 else 0.0
        except:
            return 0.0
    
    def render_bbox_snippet(
        self,
        pdf_bytes: bytes,
        page_num: int,
        bbox: Tuple[float, float, float, float],
        padding: int = 10,
    ) -> bytes:
        """
        Render a snippet image from a bounding box for evidence.
        
        Args:
            pdf_bytes: PDF content
            page_num: Page number (1-indexed)
            bbox: Bounding box (x0, y0, x1, y1)
            padding: Padding around bbox in pixels
        
        Returns:
            PNG image bytes
        """
        try:
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page = pdf_doc[page_num - 1]
            
            # Expand bbox with padding
            x0, y0, x1, y1 = bbox
            clip_rect = fitz.Rect(
                max(0, x0 - padding),
                max(0, y0 - padding),
                min(page.rect.width, x1 + padding),
                min(page.rect.height, y1 + padding),
            )
            
            # Render snippet
            pix = page.get_pixmap(clip=clip_rect, dpi=150)
            img_bytes = pix.tobytes("png")
            
            pdf_doc.close()
            return img_bytes
        
        except Exception as e:
            logger.error(f"Failed to render bbox snippet: {e}")
            raise
