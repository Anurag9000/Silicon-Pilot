"""
Alternative Suggestion Engine

Finds alternative parts based on:
1. Pin compatibility (same package, same pinout)
2. Functional equivalence (same specs within tolerance)
3. Cost optimization
4. Availability optimization
5. Second-source diversity

Ranking algorithm considers:
- Cost difference
- Availability
- Vendor diversity
- Lifecycle status
- Specification match quality
"""

import asyncpg
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import uuid


class AlternativeType(Enum):
    """Type of alternative"""
    PIN_COMPATIBLE = "pin_compatible"
    FUNCTIONALLY_EQUIVALENT = "functionally_equivalent"
    COST_OPTIMIZED = "cost_optimized"
    AVAILABILITY_OPTIMIZED = "availability_optimized"
    SECOND_SOURCE = "second_source"


@dataclass
class Alternative:
    """Alternative part suggestion"""
    part_id: uuid.UUID
    mpn: str
    manufacturer: str
    category: str
    alternative_type: AlternativeType
    score: float
    cost_difference_percent: Optional[float]
    availability_status: str
    lifecycle_status: str
    spec_match_percent: float
    reason: str


class AlternativeSuggester:
    """Suggest alternative parts"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
    
    async def find_mcu_alternatives(self, original_part_id: uuid.UUID,
                                   max_results: int = 5) -> List[Alternative]:
        """
        Find alternative MCUs
        
        Criteria:
        - Same or compatible core (ARM Cortex-M4 vs M4F acceptable)
        - Flash size >= original (within 20% tolerance)
        - RAM size >= original
        - Same or more peripherals
        - Pin count compatible (same or more)
        """
        conn = await asyncpg.connect(self.db_url)
        
        try:
            # Get original part specs
            original = await conn.fetchrow("""
                SELECT p.*, m.core, m.flash_kb, m.ram_kb, m.max_freq_mhz,
                       m.package, m.pin_count, m.voltage_min_v, m.voltage_max_v
                FROM parts p
                JOIN mcu_specs m ON p.id = m.part_id
                WHERE p.id = $1
            """, original_part_id)
            
            if not original:
                return []
            
            # Find candidates
            candidates = await conn.fetch("""
                SELECT p.*, m.core, m.flash_kb, m.ram_kb, m.max_freq_mhz,
                       m.package, m.pin_count, m.voltage_min_v, m.voltage_max_v
                FROM parts p
                JOIN mcu_specs m ON p.id = m.part_id
                WHERE p.category = 'mcu'
                  AND p.id != $1
                  AND p.status = 'active'
                  AND m.flash_kb >= $2 * 0.8  -- Within 20% tolerance
                  AND m.ram_kb >= $3
                  AND m.pin_count >= $4
                ORDER BY 
                    ABS(m.flash_kb - $2) ASC,
                    ABS(m.ram_kb - $3) ASC
                LIMIT 20
            """, original_part_id, original['flash_kb'], original['ram_kb'], original['pin_count'])
            
            alternatives = []
            
            for candidate in candidates:
                # Calculate spec match percentage
                flash_match = min(100, (min(candidate['flash_kb'], original['flash_kb']) / 
                                       max(candidate['flash_kb'], original['flash_kb'])) * 100)
                ram_match = min(100, (min(candidate['ram_kb'], original['ram_kb']) / 
                                     max(candidate['ram_kb'], original['ram_kb'])) * 100)
                freq_match = min(100, (min(candidate['max_freq_mhz'], original['max_freq_mhz']) / 
                                      max(candidate['max_freq_mhz'], original['max_freq_mhz'])) * 100)
                
                spec_match = (flash_match + ram_match + freq_match) / 3
                
                # Determine alternative type
                alt_type = AlternativeType.FUNCTIONALLY_EQUIVALENT
                if candidate['package'] == original['package'] and candidate['pin_count'] == original['pin_count']:
                    alt_type = AlternativeType.PIN_COMPATIBLE
                if candidate['manufacturer'] != original['manufacturer']:
                    alt_type = AlternativeType.SECOND_SOURCE
                
                # Calculate score (higher is better)
                score = spec_match
                if alt_type == AlternativeType.PIN_COMPATIBLE:
                    score += 20  # Bonus for pin compatibility
                if candidate['manufacturer'] != original['manufacturer']:
                    score += 10  # Bonus for vendor diversity
                
                # Build reason
                reasons = []
                if candidate['flash_kb'] > original['flash_kb']:
                    reasons.append(f"+{candidate['flash_kb'] - original['flash_kb']}KB Flash")
                if candidate['ram_kb'] > original['ram_kb']:
                    reasons.append(f"+{candidate['ram_kb'] - original['ram_kb']}KB RAM")
                if candidate['max_freq_mhz'] > original['max_freq_mhz']:
                    reasons.append(f"+{candidate['max_freq_mhz'] - original['max_freq_mhz']}MHz")
                if alt_type == AlternativeType.PIN_COMPATIBLE:
                    reasons.append("Pin-compatible")
                if candidate['manufacturer'] != original['manufacturer']:
                    reasons.append("Second source")
                
                reason = ", ".join(reasons) if reasons else "Similar specs"
                
                alternatives.append(Alternative(
                    part_id=candidate['id'],
                    mpn=candidate['mpn'],
                    manufacturer=candidate['manufacturer'],
                    category=candidate['category'],
                    alternative_type=alt_type,
                    score=score,
                    cost_difference_percent=None,  # TODO: Add pricing data
                    availability_status="unknown",  # TODO: Add availability data
                    lifecycle_status="active",
                    spec_match_percent=spec_match,
                    reason=reason
                ))
            
            # Sort by score and return top N
            alternatives.sort(key=lambda x: x.score, reverse=True)
            return alternatives[:max_results]
            
        finally:
            await conn.close()
    
    async def find_pmic_alternatives(self, original_part_id: uuid.UUID,
                                    max_results: int = 5) -> List[Alternative]:
        """Find alternative PMICs"""
        conn = await asyncpg.connect(self.db_url)
        
        try:
            # Get original PMIC specs
            original = await conn.fetchrow("""
                SELECT p.*, pm.input_voltage_min_v, pm.input_voltage_max_v,
                       pm.output_voltage_min_v, pm.output_voltage_max_v,
                       pm.output_current_max_a, pm.num_channels, pm.efficiency_percent
                FROM parts p
                JOIN pmic_specs pm ON p.id = pm.part_id
                WHERE p.id = $1
            """, original_part_id)
            
            if not original:
                return []
            
            # Find candidates with similar specs
            candidates = await conn.fetch("""
                SELECT p.*, pm.input_voltage_min_v, pm.input_voltage_max_v,
                       pm.output_voltage_min_v, pm.output_voltage_max_v,
                       pm.output_current_max_a, pm.num_channels, pm.efficiency_percent
                FROM parts p
                JOIN pmic_specs pm ON p.id = pm.part_id
                WHERE p.category = 'pmic'
                  AND p.id != $1
                  AND p.status = 'active'
                  AND pm.output_current_max_a >= $2 * 0.9
                  AND pm.num_channels >= $3
                LIMIT 20
            """, original_part_id, original['output_current_max_a'], original['num_channels'])
            
            alternatives = []
            
            for candidate in candidates:
                # Calculate spec match
                current_match = min(100, (min(candidate['output_current_max_a'], original['output_current_max_a']) / 
                                         max(candidate['output_current_max_a'], original['output_current_max_a'])) * 100)
                
                spec_match = current_match
                score = spec_match
                
                if candidate['manufacturer'] != original['manufacturer']:
                    score += 10
                
                reason = f"{candidate['num_channels']} channels, {candidate['output_current_max_a']:.2f}A"
                
                alternatives.append(Alternative(
                    part_id=candidate['id'],
                    mpn=candidate['mpn'],
                    manufacturer=candidate['manufacturer'],
                    category=candidate['category'],
                    alternative_type=AlternativeType.FUNCTIONALLY_EQUIVALENT,
                    score=score,
                    cost_difference_percent=None,
                    availability_status="unknown",
                    lifecycle_status="active",
                    spec_match_percent=spec_match,
                    reason=reason
                ))
            
            alternatives.sort(key=lambda x: x.score, reverse=True)
            return alternatives[:max_results]
            
        finally:
            await conn.close()
    
    async def find_alternatives(self, part_id: uuid.UUID, max_results: int = 5) -> List[Alternative]:
        """Find alternatives for any part category"""
        conn = await asyncpg.connect(self.db_url)
        
        try:
            # Determine category
            category = await conn.fetchval("SELECT category FROM parts WHERE id = $1", part_id)
            
            if category == "mcu":
                return await self.find_mcu_alternatives(part_id, max_results)
            elif category == "pmic":
                return await self.find_pmic_alternatives(part_id, max_results)
            else:
                return []
                
        finally:
            await conn.close()


# Example usage
async def main():
    import os
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")
    suggester = AlternativeSuggester(db_url)
    
    # Example: Find alternatives for a part
    # part_id = uuid.UUID("...")  # Replace with actual part ID
    # alternatives = await suggester.find_alternatives(part_id)
    # 
    # for alt in alternatives:
    #     print(f"{alt.mpn} ({alt.manufacturer})")
    #     print(f"  Type: {alt.alternative_type.value}")
    #     print(f"  Score: {alt.score:.1f}")
    #     print(f"  Match: {alt.spec_match_percent:.1f}%")
    #     print(f"  Reason: {alt.reason}")
    #     print()


if __name__ == "__main__":
    import asyncio
    import sys
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
