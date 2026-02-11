
"""
STM32 Errata Sheet Extractor

Parses "Silicon Limitations" from Errata Sheet PDFs.
Extracts:
- Limitation Title/Code (e.g. 2.1.3)
- Description
- Workaround
- Affected Revisions (Heuristic)
"""

import pdfplumber
import re
import logging
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ErrataItem:
    code: str
    title: str
    module: str
    description: str
    workaround: str
    affected_revisions: List[str]

class STM32ErrataExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def extract_errata(self) -> List[ErrataItem]:
        """
        Scans values looking for limitation patterns.
        """
        items = []
        text_content = ""
        
        # 1. Extract all text
        # Optimization: Limit pages? Errata sheets are usually small (<50 pages).
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text_content += extracted + "\n"
        except Exception as e:
            logger.error(f"Failed to read PDF {self.pdf_path}: {e}")
            return []

        # 2. Identify Limitation Blocks
        # Pattern: 2.x.x Title
        # followed by "Description"
        # followed by "Workaround"
        
        # Regex to split by section headers like "2.1.1 Title"
        # Assumption: Section headers start at start of line
        
        # Finding the start of the "Silicon limitations" section would be good, 
        # but searching whole text for patterns is more robust against TOCs.
        
        # Regex:
        # ^(\d+\.\d+\.\d+)\s+(.+?)$  (Multiline)
        
        # We'll split the text into chunks starting with the section header
        
        # Normalize newlines
        text_content = text_content.replace('\r\n', '\n')
        
        # Find all section headers
        # Matches: "2.1.3 I2C analog filter..."
        header_pattern = re.compile(r'\n(\d+\.\d+\.\d+)\s+([^\n]+)')
        
        matches = list(header_pattern.finditer(text_content))
        
        for i, match in enumerate(matches):
            code = match.group(1)
            title = match.group(2).strip()
            start_idx = match.end()
            
            # End index is the start of the next match (or EOF)
            end_idx = matches[i+1].start() if i + 1 < len(matches) else len(text_content)
            
            block_text = text_content[start_idx:end_idx]
            
            # Simple Heuristic: A block is an errata if it contains "Description" AND "Workaround"
            # (Case insensitive)
            
            if "description" in block_text.lower() and "workaround" in block_text.lower():
                # Extract Description
                desc_match = re.search(r'Description[:\s]+(.*?)(?=Workaround[:\s]|$)', block_text, re.IGNORECASE | re.DOTALL)
                description = desc_match.group(1).strip() if desc_match else ""
                
                # Extract Workaround
                work_match = re.search(r'Workaround[:\s]+(.*?)$', block_text, re.IGNORECASE | re.DOTALL)
                workaround = work_match.group(1).strip() if work_match else ""
                
                # Extract Module from title or code?
                # e.g. "2.1.3 I2C..." -> Module I2C
                # Heuristic: First word of title
                module = title.split(' ')[0] if title else "System"
                
                # Affected Revisions? 
                # Hard to parse reliably without table context.
                # Only if "Revision A" is mentioned?
                affected = []
                
                item = ErrataItem(
                    code=code,
                    title=title,
                    module=module,
                    description=description,
                    workaround=workaround,
                    affected_revisions=affected
                )
                items.append(item)
                
        logger.info(f"Extracted {len(items)} errata items from {self.pdf_path}")
        return items

    async def save_to_db(self, conn, document_id: str):
        items = self.extract_errata()
        
        # Clear existing
        await conn.execute("DELETE FROM errata_items WHERE document_id = $1", document_id)
        
        for item in items:
            await conn.execute("""
                INSERT INTO errata_items (
                    document_id, code, module, title, description, workaround, affected_revisions
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, document_id, item.code, item.module, item.title, item.description, item.workaround, item.affected_revisions)
