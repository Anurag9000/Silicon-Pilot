"""
Reference Design Matcher

Finds reference designs that match user requirements:
- Similar MCU (same family or core)
- Similar application area
- Similar power requirements
- Available documentation

Helps users bootstrap their designs from proven reference implementations.
"""

import asyncpg
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import uuid


@dataclass
class ReferenceDesignMatch:
    """Matched reference design"""
    design_id: uuid.UUID
    design_name: str
    design_code: str
    manufacturer: str
    application_area: str
    description: str
    match_score: float
    match_reasons: List[str]
    schematic_url: Optional[str]
    bom_url: Optional[str]
    documentation_url: Optional[str]
    key_parts: List[Dict[str, Any]]


class ReferenceDesignMatcher:
    """Match user requirements to reference designs"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
    
    async def find_by_mcu(self, mcu_id: uuid.UUID, max_results: int = 5) -> List[ReferenceDesignMatch]:
        """
        Find reference designs using the same or similar MCU
        """
        conn = await asyncpg.connect(self.db_url)
        
        try:
            # Get MCU details
            mcu = await conn.fetchrow("""
                SELECT p.mpn, p.manufacturer, m.core, m.flash_kb, m.ram_kb
                FROM parts p
                JOIN mcu_specs m ON p.id = m.part_id
                WHERE p.id = $1
            """, mcu_id)
            
            if not mcu:
                return []
            
            # Find designs with exact MCU match
            exact_matches = await conn.fetch("""
                SELECT rd.*, COUNT(rdp.id) as part_count
                FROM reference_designs rd
                JOIN reference_design_parts rdp ON rd.id = rdp.design_id
                WHERE rdp.part_id = $1
                GROUP BY rd.id
                ORDER BY part_count DESC
                LIMIT $2
            """, mcu_id, max_results)
            
            matches = []
            
            for design in exact_matches:
                # Get key parts for this design
                key_parts = await conn.fetch("""
                    SELECT p.mpn, p.manufacturer, p.category, rdp.reference_designator
                    FROM reference_design_parts rdp
                    JOIN parts p ON rdp.part_id = p.id
                    WHERE rdp.design_id = $1 AND rdp.is_critical = TRUE
                    LIMIT 5
                """, design['id'])
                
                matches.append(ReferenceDesignMatch(
                    design_id=design['id'],
                    design_name=design['design_name'],
                    design_code=design['design_id'] or '',
                    manufacturer=design['manufacturer'],
                    application_area=design['application_area'] or 'General',
                    description=design['description'] or '',
                    match_score=100.0,  # Exact MCU match
                    match_reasons=[f"Uses {mcu['mpn']}", "Exact MCU match"],
                    schematic_url=design['schematic_url'],
                    bom_url=design['bom_url'],
                    documentation_url=design['documentation_url'],
                    key_parts=[{
                        'mpn': p['mpn'],
                        'manufacturer': p['manufacturer'],
                        'category': p['category'],
                        'designator': p['reference_designator']
                    } for p in key_parts]
                ))
            
            return matches
            
        finally:
            await conn.close()
    
    async def find_by_application(self, application_area: str, 
                                  max_results: int = 10) -> List[ReferenceDesignMatch]:
        """
        Find reference designs for a specific application area
        """
        conn = await asyncpg.connect(self.db_url)
        
        try:
            designs = await conn.fetch("""
                SELECT * FROM reference_designs
                WHERE application_area ILIKE $1
                ORDER BY created_at DESC
                LIMIT $2
            """, f"%{application_area}%", max_results)
            
            matches = []
            
            for design in designs:
                # Get key parts
                key_parts = await conn.fetch("""
                    SELECT p.mpn, p.manufacturer, p.category, rdp.reference_designator
                    FROM reference_design_parts rdp
                    JOIN parts p ON rdp.part_id = p.id
                    WHERE rdp.design_id = $1 AND rdp.is_critical = TRUE
                    LIMIT 5
                """, design['id'])
                
                matches.append(ReferenceDesignMatch(
                    design_id=design['id'],
                    design_name=design['design_name'],
                    design_code=design['design_id'] or '',
                    manufacturer=design['manufacturer'],
                    application_area=design['application_area'] or 'General',
                    description=design['description'] or '',
                    match_score=80.0,  # Application area match
                    match_reasons=[f"Application: {design['application_area']}"],
                    schematic_url=design['schematic_url'],
                    bom_url=design['bom_url'],
                    documentation_url=design['documentation_url'],
                    key_parts=[{
                        'mpn': p['mpn'],
                        'manufacturer': p['manufacturer'],
                        'category': p['category'],
                        'designator': p['reference_designator']
                    } for p in key_parts]
                ))
            
            return matches
            
        finally:
            await conn.close()
    
    async def find_by_manufacturer(self, manufacturer: str,
                                   max_results: int = 10) -> List[ReferenceDesignMatch]:
        """
        Find reference designs from a specific manufacturer
        """
        conn = await asyncpg.connect(self.db_url)
        
        try:
            designs = await conn.fetch("""
                SELECT * FROM reference_designs
                WHERE manufacturer ILIKE $1
                ORDER BY created_at DESC
                LIMIT $2
            """, f"%{manufacturer}%", max_results)
            
            matches = []
            
            for design in designs:
                key_parts = await conn.fetch("""
                    SELECT p.mpn, p.manufacturer, p.category, rdp.reference_designator
                    FROM reference_design_parts rdp
                    JOIN parts p ON rdp.part_id = p.id
                    WHERE rdp.design_id = $1 AND rdp.is_critical = TRUE
                    LIMIT 5
                """, design['id'])
                
                matches.append(ReferenceDesignMatch(
                    design_id=design['id'],
                    design_name=design['design_name'],
                    design_code=design['design_id'] or '',
                    manufacturer=design['manufacturer'],
                    application_area=design['application_area'] or 'General',
                    description=design['description'] or '',
                    match_score=70.0,
                    match_reasons=[f"From {manufacturer}"],
                    schematic_url=design['schematic_url'],
                    bom_url=design['bom_url'],
                    documentation_url=design['documentation_url'],
                    key_parts=[{
                        'mpn': p['mpn'],
                        'manufacturer': p['manufacturer'],
                        'category': p['category'],
                        'designator': p['reference_designator']
                    } for p in key_parts]
                ))
            
            return matches
            
        finally:
            await conn.close()
    
    async def add_reference_design(self, design_name: str, manufacturer: str,
                                  application_area: str, description: str,
                                  schematic_url: Optional[str] = None,
                                  bom_url: Optional[str] = None,
                                  documentation_url: Optional[str] = None) -> uuid.UUID:
        """
        Add a new reference design to the database
        """
        conn = await asyncpg.connect(self.db_url)
        
        try:
            design_id = await conn.fetchval("""
                INSERT INTO reference_designs (
                    design_name, manufacturer, application_area, description,
                    schematic_url, bom_url, documentation_url
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """, design_name, manufacturer, application_area, description,
                schematic_url, bom_url, documentation_url)
            
            return design_id
            
        finally:
            await conn.close()
    
    async def add_design_part(self, design_id: uuid.UUID, part_id: uuid.UUID,
                             reference_designator: str, quantity: int = 1,
                             is_critical: bool = False) -> uuid.UUID:
        """
        Add a part to a reference design BOM
        """
        conn = await asyncpg.connect(self.db_url)
        
        try:
            part_entry_id = await conn.fetchval("""
                INSERT INTO reference_design_parts (
                    design_id, part_id, reference_designator, quantity, is_critical
                ) VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, design_id, part_id, reference_designator, quantity, is_critical)
            
            return part_entry_id
            
        finally:
            await conn.close()


# Example usage
async def main():
    import os
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")
    matcher = ReferenceDesignMatcher(db_url)
    
    # Example: Find designs by application
    # matches = await matcher.find_by_application("Motor Control")
    # 
    # for match in matches:
    #     print(f"\n{match.design_name} ({match.design_code})")
    #     print(f"  Manufacturer: {match.manufacturer}")
    #     print(f"  Application: {match.application_area}")
    #     print(f"  Match Score: {match.match_score:.1f}")
    #     print(f"  Key Parts:")
    #     for part in match.key_parts:
    #         print(f"    - {part['designator']}: {part['mpn']} ({part['category']})")


if __name__ == "__main__":
    import asyncio
    import sys
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
