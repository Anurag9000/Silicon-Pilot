"""
Complete STM32 Ingestion Script

Downloads STM32 datasheets, parses them, extracts specs, and populates database.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any
import json
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.stm32_downloader import STM32DatasheetDownloader
from ingestion.stm32_parser import STM32OrderingCodeParser
from ingestion.pdf_parser import PDFParser
from ingestion.extractor import FieldExtractor
from core.database import get_pool
import asyncpg


class STM32CompleteIngester:
    """Complete STM32 ingestion pipeline"""
    
    def __init__(self):
        self.downloader = STM32DatasheetDownloader()
        self.ordering_parser = STM32OrderingCodeParser()
        self.pdf_parser = PDFParser()
        self.field_extractor = FieldExtractor()
        self.pool: asyncpg.Pool = None
    
    async def initialize(self):
        """Initialize database connection"""
        self.pool = await get_pool()
        print("[OK] Database connected")
    
    async def ingest_all(self):
        """Complete ingestion pipeline"""
        
        total_inserted = 0
        
        print("\n" + "="*60)
        print("STM32 COMPLETE INGESTION PIPELINE")
        print("="*60 + "\n")
        
        # Step 1: Download datasheets
        print("STEP 1: Downloading STM32 Datasheets")
        print("-" * 60)
        download_results = self.downloader.download_all()
        
        total_pdfs = sum(len(paths) for paths in download_results.values())
        print(f"[OK] {total_pdfs} datasheets ready\n")
        
        # Step 2: Parse and extract from PDFs
        print("STEP 2: Parsing PDFs and Extracting Specs")
        print("-" * 60)
        
        all_parts = []
        
        for family, pdf_paths in download_results.items():
            family_parts = []
            print(f"\nProcessing {family} family ({len(pdf_paths)} datasheets)...")
            
            for pdf_path in pdf_paths:
                try:
                    # Parse PDF
                    pdf_result = self.pdf_parser.parse(str(pdf_path))
                    
                    # Extract part number from filename
                    base_name = pdf_path.stem.upper()
                    
                    # Generate variants
                    variants = self._generate_variants(base_name, family)
                    
                    count = 0
                    for variant_mpn in variants:
                        # Parse ordering code
                        parsed = self.ordering_parser.parse(variant_mpn)
                        
                        if "error" in parsed:
                            continue
                        
                        # Extract additional specs from PDF text
                        # Optimization: only join text once per PDF
                        pdf_text = " ".join([page.get("text", "") for page in pdf_result.get("pages", [])])
                        extracted_specs = self.field_extractor.extract_all_with_metadata(pdf_text)
                        
                        # Flatten for parts table
                        flat_specs = {}
                        for k, v in extracted_specs.items():
                             if isinstance(v, dict) and "normalized_value" in v:
                                 flat_specs[k] = v["normalized_value"]
                             else:
                                 flat_specs[k] = v
                        
                        # Merge parsed + extracted
                        part_data = {
                            **parsed,
                            **flat_specs,      # Contains scalar values for DB insert
                            "evidence_metadata": extracted_specs, # Full metadata for snippets
                            "status": "active",
                            "document_url": f"file://{pdf_path}",
                            "document_hash": pdf_result.get("hash", ""),
                        }
                        
                        family_parts.append(part_data)
                        count += 1
                    
                    print(f"  [OK] {pdf_path.name}: {count} variants")
                    
                except Exception as e:
                    print(f"  [FAIL] {pdf_path.name}: {e}")
            
            # Insert family parts immediately
            if family_parts:
                print(f"  Inserting {len(family_parts)} parts for {family}...")
                inserted = await self._insert_parts(family_parts)
                total_inserted += inserted
                print(f"  [OK] Inserted {inserted} parts")
                
        print(f"\n[OK] Ingestion complete. Total parts: {total_inserted}\n")
        
        # Step 4: Summary
        print("="*60)
        print("INGESTION COMPLETE")
        print("="*60)
        print(f"Total parts in database: {total_inserted}")
        print(f"Families covered: {', '.join(download_results.keys())}")
        print()
    
    def _generate_variants(self, base_mpn: str, family: str) -> List[str]:
        """
        Generate common variants from a base part number.
        
        For example, STM32F405RG might have variants:
        - STM32F405RGT6 (LQFP64)
        - STM32F405RGH6 (BGA64)
        """
        # Simplified: just add common package/temp suffixes
        suffixes = [
            "T6",  # LQFP, standard temp
            "H6",  # BGA, standard temp
            "V6",  # LQFP100, standard temp
        ]
        
        variants = []
        for suffix in suffixes:
            # If base MPN is already complete, use it
            if len(base_mpn) >= 13:
                variants.append(base_mpn)
                break
            else:
                # Append suffix
                variant = base_mpn + suffix
                variants.append(variant)
        
        return variants
    
    async def _insert_parts(self, parts: List[Dict[str, Any]]) -> int:
        """Insert parts into database"""
        inserted = 0
        
        async with self.pool.acquire() as conn:
            for part in parts:
                try:
                    # Insert into parts table
                    part_id = await conn.fetchval("""
                        INSERT INTO parts (
                            mpn, manufacturer, family, status,
                            package_family, package_name, pin_count,
                            temp_min_c, temp_max_c
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        ON CONFLICT (mpn) DO UPDATE SET
                            status = EXCLUDED.status
                        RETURNING id
                    """,
                        part.get("mpn"),
                        part.get("manufacturer", "STMicroelectronics"),
                        part.get("family", "STM32"),
                        part.get("status", "active"),
                        part.get("package_family", "LQFP"),
                        part.get("package_family", "LQFP"),
                        part.get("pin_count", 64),
                        part.get("temp_min_c", -40),
                        part.get("temp_max_c", 85),
                    )
                    
                    # Insert into mcu_specs table
                    await conn.execute("""
                        INSERT INTO mcu_specs (
                            part_id, core, max_mhz, flash_kb, sram_kb,
                            can_count, uart_count, spi_count, i2c_count,
                            usb_fs, ethernet, has_fpu
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                        ON CONFLICT (part_id) DO UPDATE SET
                            core = EXCLUDED.core,
                            flash_kb = EXCLUDED.flash_kb
                    """,
                        part_id,
                        part.get("core", "Cortex-M4"),
                        part.get("clock_speed_mhz", 168),
                        part.get("flash_kb", 512),
                        part.get("sram_kb", 128),
                        part.get("can_count", 2),
                        part.get("uart_count", 4),
                        part.get("spi_count", 3),
                        part.get("i2c_count", 3),
                        part.get("usb_fs", True),
                        part.get("ethernet", False),
                        part.get("has_fpu", True),
                    )
                    
                    # Insert document record
                    doc_id = await conn.fetchval("""
                        INSERT INTO documents (
                            source_url, source_type, doc_hash, content_type
                        ) VALUES ($1, $2, $3, $4)
                        ON CONFLICT (source_url) DO UPDATE SET
                            doc_hash = EXCLUDED.doc_hash
                        RETURNING id
                    """,
                        part.get("document_url", ""),
                        "mfg_pdf",
                        part.get("document_hash", ""),
                        "application/pdf",
                    )
                    
                    # Insert evidence records with snippets
                    # Ensure snippets directory exists
                    snippets_dir = Path("data/snippets")
                    snippets_dir.mkdir(parents=True, exist_ok=True)
                    
                    # We need the PDF bytes for snippet rendering
                    # This is inefficient (reading file again) but safe for MVP
                    try:
                        pdf_bytes = Path(part["document_url"].replace("file://", "")).read_bytes()
                    except Exception as e:
                        print(f"  [WARN] Could not read PDF for snippets: {e}")
                        pdf_bytes = None
                    
                    evidence_meta = part.get("evidence_metadata", {})

                    for field, value in evidence_meta.items():
                         # Skip if not metadata dict
                        if not isinstance(value, dict) or "bbox" not in value:
                             continue
                             
                        # It is a metadata dict
                        evidence_id = uuid.uuid4()
                        snippet_key = None
                        
                        if pdf_bytes and value.get("bbox"):
                            try:
                                snippet_filename = f"{evidence_id}.png"
                                snippet_path = snippets_dir / snippet_filename
                                
                                # Render snippet
                                img_bytes = self.pdf_parser.render_bbox_snippet(
                                    pdf_bytes,
                                    value.get("page", 1),
                                    value.get("bbox")
                                )
                                
                                # Save to disk
                                snippet_path.write_bytes(img_bytes)
                                snippet_key = str(snippet_path)
                                
                            except Exception as e:
                                # Log but don't fail ingestion
                                # print(f"  [WARN] Snippet generation failed for {field}: {e}")
                                pass

                        # Insert into evidence table
                        await conn.execute("""
                            INSERT INTO evidence (
                                id, part_id, field_path, 
                                extracted_value_raw, normalized_value,
                                document_id, page, bbox, snippet_storage_key,
                                confidence, parser_version
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        """,
                            evidence_id,
                            part_id,
                            f"mcu_specs.{field}",
                            value.get("raw_value"),
                            json.dumps({"value": value.get("normalized_value")}),
                            doc_id,
                            value.get("page", 1),
                            json.dumps(value.get("bbox")),
                            snippet_key,
                            0.95, # Confidence placeholder
                            "v1.0"
                        )

                    inserted += 1
                    
                    if inserted % 10 == 0:
                        print(f"  Inserted {inserted} parts...")
                
                except Exception as e:
                    print(f"  [FAIL] Failed to insert {part.get('mpn', 'unknown')}: {e}")
        
        return inserted
    
    async def close(self):
        """Close database connection"""
        if self.pool:
            await self.pool.close()


async def main():
    """Run complete ingestion"""
    ingester = STM32CompleteIngester()
    
    try:
        await ingester.initialize()
        await ingester.ingest_all()
    finally:
        await ingester.close()


if __name__ == "__main__":
    asyncio.run(main())
