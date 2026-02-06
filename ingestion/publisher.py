"""
Publisher

Publish validated extractions to database with confidence thresholds
and transaction management.
"""

import logging
from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
import asyncpg

from core.models import (
    PartBase,
    MCUSpecBase,
    EvidenceRecord,
    DocumentRecord,
    Conflict,
    PartStatus,
)

logger = logging.getLogger(__name__)


class Publisher:
    """Publish validated data to database"""
    
    def __init__(
        self,
        db_pool: asyncpg.Pool,
        confidence_threshold: float = 0.85,
    ):
        """
        Initialize publisher.
        
        Args:
            db_pool: AsyncPG connection pool
            confidence_threshold: Minimum confidence for auto-publishing
        """
        self.db_pool = db_pool
        self.confidence_threshold = confidence_threshold
    
    async def publish_part(
        self,
        mpn: str,
        manufacturer: str,
        family: str,
        part_data: Dict[str, Any],
        evidence_list: List[EvidenceRecord],
        document: DocumentRecord,
        conflicts: List[Conflict],
    ) -> UUID:
        """
        Publish a complete part with specs and evidence.
        
        Args:
            mpn: Manufacturer part number
            manufacturer: Manufacturer name
            family: Part family
            part_data: Complete part specification
            evidence_list: Evidence records
            document: Source document
            conflicts: Detected conflicts
        
        Returns:
            Part ID (UUID)
        """
        logger.info(f"Publishing part: {mpn}")
        
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # 1. Insert or update document
                doc_id = await self._upsert_document(conn, document)
                
                # 2. Insert or update part
                part_id = await self._upsert_part(
                    conn,
                    mpn,
                    manufacturer,
                    family,
                    part_data,
                )
                
                # 3. Insert or update MCU specs
                await self._upsert_mcu_specs(conn, part_id, part_data)
                
                # 4. Insert evidence records
                for evidence in evidence_list:
                    evidence.part_id = part_id
                    evidence.document_id = doc_id
                    
                    # Only publish if confidence meets threshold
                    if evidence.confidence >= self.confidence_threshold:
                        await self._insert_evidence(conn, evidence)
                    else:
                        logger.info(
                            f"Skipping low-confidence evidence for {evidence.field_path}: "
                            f"{evidence.confidence:.3f} < {self.confidence_threshold}"
                        )
                
                # 5. Insert conflicts
                for conflict in conflicts:
                    conflict.part_id = part_id
                    await self._insert_conflict(conn, conflict)
                
                logger.info(f"Published part {mpn} with ID {part_id}")
                
                return part_id
    
    async def _upsert_document(
        self,
        conn: asyncpg.Connection,
        document: DocumentRecord,
    ) -> UUID:
        """Insert or update document record"""
        
        # Check if document exists
        existing = await conn.fetchrow(
            """
            SELECT id FROM documents
            WHERE source_url = $1 AND doc_hash = $2
            """,
            document.source_url,
            document.doc_hash,
        )
        
        if existing:
            return existing['id']
        
        # Insert new document
        doc_id = uuid4()
        
        await conn.execute(
            """
            INSERT INTO documents (
                id, source_url, source_type, doc_hash, content_type,
                storage_key, version, fetched_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            doc_id,
            document.source_url,
            document.source_type.value,
            document.doc_hash,
            document.content_type,
            document.storage_key,
            document.version,
            document.fetched_at,
        )
        
        return doc_id
    
    async def _upsert_part(
        self,
        conn: asyncpg.Connection,
        mpn: str,
        manufacturer: str,
        family: str,
        part_data: Dict[str, Any],
    ) -> UUID:
        """Insert or update part record"""
        
        # Check if part exists
        existing = await conn.fetchrow(
            "SELECT id FROM parts WHERE mpn = $1",
            mpn,
        )
        
        if existing:
            part_id = existing['id']
            
            # Update part
            await conn.execute(
                """
                UPDATE parts SET
                    manufacturer = $2,
                    family = $3,
                    status = $4,
                    package_family = $5,
                    package_name = $6,
                    pin_count = $7,
                    temp_min_c = $8,
                    temp_max_c = $9,
                    updated_at = NOW()
                WHERE id = $1
                """,
                part_id,
                manufacturer,
                family,
                part_data.get('status', 'active'),
                part_data.get('package_family'),
                part_data.get('package_name'),
                part_data.get('pin_count'),
                part_data.get('temp_min_c'),
                part_data.get('temp_max_c'),
            )
        else:
            # Insert new part
            part_id = uuid4()
            
            await conn.execute(
                """
                INSERT INTO parts (
                    id, mpn, manufacturer, family, status,
                    package_family, package_name, pin_count,
                    temp_min_c, temp_max_c
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                part_id,
                mpn,
                manufacturer,
                family,
                part_data.get('status', 'active'),
                part_data.get('package_family'),
                part_data.get('package_name'),
                part_data.get('pin_count'),
                part_data.get('temp_min_c'),
                part_data.get('temp_max_c'),
            )
        
        return part_id
    
    async def _upsert_mcu_specs(
        self,
        conn: asyncpg.Connection,
        part_id: UUID,
        part_data: Dict[str, Any],
    ):
        """Insert or update MCU specs"""
        
        # Check if specs exist
        existing = await conn.fetchrow(
            "SELECT id FROM mcu_specs WHERE part_id = $1",
            part_id,
        )
        
        if existing:
            # Update specs
            await conn.execute(
                """
                UPDATE mcu_specs SET
                    core = $2,
                    max_mhz = $3,
                    flash_kb = $4,
                    sram_kb = $5,
                    eeprom_kb = $6,
                    can_count = $7,
                    can_fd_count = $8,
                    uart_count = $9,
                    spi_count = $10,
                    i2c_count = $11,
                    usb_fs = $12,
                    usb_hs = $13,
                    ethernet = $14,
                    adc_channels = $15,
                    dac_channels = $16,
                    timers_count = $17,
                    pwm_channels = $18,
                    has_fpu = $19,
                    has_dsp = $20,
                    has_crypto = $21,
                    has_wireless = $22,
                    vdd_min_v = $23,
                    vdd_max_v = $24,
                    active_ma = $25,
                    standby_ua = $26,
                    sleep_ua = $27,
                    cost_usd = $28,
                    extras = $29,
                    updated_at = NOW()
                WHERE part_id = $1
                """,
                part_id,
                part_data.get('core'),
                part_data.get('max_mhz'),
                part_data.get('flash_kb'),
                part_data.get('sram_kb'),
                part_data.get('eeprom_kb'),
                part_data.get('can_count', 0),
                part_data.get('can_fd_count', 0),
                part_data.get('uart_count', 0),
                part_data.get('spi_count', 0),
                part_data.get('i2c_count', 0),
                part_data.get('usb_fs', False),
                part_data.get('usb_hs', False),
                part_data.get('ethernet', False),
                part_data.get('adc_channels', 0),
                part_data.get('dac_channels', 0),
                part_data.get('timers_count', 0),
                part_data.get('pwm_channels', 0),
                part_data.get('has_fpu', False),
                part_data.get('has_dsp', False),
                part_data.get('has_crypto', False),
                part_data.get('has_wireless', False),
                part_data.get('vdd_min_v'),
                part_data.get('vdd_max_v'),
                part_data.get('active_ma'),
                part_data.get('standby_ua'),
                part_data.get('sleep_ua'),
                part_data.get('cost_usd'),
                part_data.get('extras'),
            )
        else:
            # Insert new specs
            await conn.execute(
                """
                INSERT INTO mcu_specs (
                    part_id, core, max_mhz, flash_kb, sram_kb, eeprom_kb,
                    can_count, can_fd_count, uart_count, spi_count, i2c_count,
                    usb_fs, usb_hs, ethernet,
                    adc_channels, dac_channels, timers_count, pwm_channels,
                    has_fpu, has_dsp, has_crypto, has_wireless,
                    vdd_min_v, vdd_max_v,
                    active_ma, standby_ua, sleep_ua,
                    cost_usd, extras
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                    $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26,
                    $27, $28, $29
                )
                """,
                part_id,
                part_data.get('core'),
                part_data.get('max_mhz'),
                part_data.get('flash_kb'),
                part_data.get('sram_kb'),
                part_data.get('eeprom_kb'),
                part_data.get('can_count', 0),
                part_data.get('can_fd_count', 0),
                part_data.get('uart_count', 0),
                part_data.get('spi_count', 0),
                part_data.get('i2c_count', 0),
                part_data.get('usb_fs', False),
                part_data.get('usb_hs', False),
                part_data.get('ethernet', False),
                part_data.get('adc_channels', 0),
                part_data.get('dac_channels', 0),
                part_data.get('timers_count', 0),
                part_data.get('pwm_channels', 0),
                part_data.get('has_fpu', False),
                part_data.get('has_dsp', False),
                part_data.get('has_crypto', False),
                part_data.get('has_wireless', False),
                part_data.get('vdd_min_v'),
                part_data.get('vdd_max_v'),
                part_data.get('active_ma'),
                part_data.get('standby_ua'),
                part_data.get('sleep_ua'),
                part_data.get('cost_usd'),
                part_data.get('extras'),
            )
    
    async def _insert_evidence(
        self,
        conn: asyncpg.Connection,
        evidence: EvidenceRecord,
    ):
        """Insert evidence record"""
        
        evidence_id = evidence.id or uuid4()
        
        await conn.execute(
            """
            INSERT INTO evidence (
                id, part_id, field_path,
                extracted_value_raw, normalized_value,
                document_id, page, bbox, snippet_storage_key,
                confidence, parser_version, extracted_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ON CONFLICT (id) DO NOTHING
            """,
            evidence_id,
            evidence.part_id,
            evidence.field_path,
            evidence.extracted_value_raw,
            evidence.normalized_value,
            evidence.document_id,
            evidence.page,
            evidence.bbox,
            evidence.snippet_storage_key,
            evidence.confidence,
            evidence.parser_version,
            evidence.extracted_at,
        )
    
    async def _insert_conflict(
        self,
        conn: asyncpg.Connection,
        conflict: Conflict,
    ):
        """Insert conflict record"""
        
        conflict_id = conflict.id or uuid4()
        
        await conn.execute(
            """
            INSERT INTO conflicts (
                id, part_id, field_path, evidence_ids, status
            ) VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO NOTHING
            """,
            conflict_id,
            conflict.part_id,
            conflict.field_path,
            conflict.evidence_ids,
            conflict.status.value,
        )
