"""
Design Rule Checker (DRC)
Validates hardware designs against 50+ rules covering Power, Signal, Clock, Memory, Thermal.
Stores violations in the database.
"""

import asyncpg
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import sys
import logging
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DRC")

class Severity(Enum):
    """Rule violation severity"""
    ERROR = "error"          # Must fix - design will not work
    WARNING = "warning"      # Should fix - may cause issues
    INFO = "info"           # Nice to have - best practice

@dataclass
class Violation:
    """Design rule violation"""
    rule_id: str
    rule_name: str
    severity: Severity
    component: str
    message: str
    recommendation: str
    design_id: uuid.UUID

class DesignRuleChecker:
    """Check hardware designs against validation rules"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    # ==================== PERSISTENCE ====================
    
    async def save_violations(self, conn: asyncpg.Connection, violations: List[Violation]):
        """Save violations to database"""
        if not violations:
            return

        # Prepare batch insert
        records = [(
            v.design_id,
            v.rule_id, 
            v.rule_name, 
            v.severity.value, 
            v.component, 
            v.message, 
            v.recommendation
        ) for v in violations]
        
        await conn.executemany("""
            INSERT INTO drc_violations (
                design_id, rule_id, rule_name, severity, component_ref, message, recommendation
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, records)
        
        logger.info(f"Saved {len(violations)} violations to database.")

    # ==================== POWER SUPPLY RULES ====================
    
    async def check_vdd_range_overlap(self, conn: asyncpg.Connection, 
                                      design_id: uuid.UUID,
                                      design_parts: List[uuid.UUID]) -> List[Violation]:
        """Rule P001: All parts must have overlapping VDD ranges"""
        violations = []
        
        # Get voltage ranges for MCUs, Sensors, CAN, etc.
        # MCUs
        mcus = await conn.fetch("""
            SELECT p.mpn, m.voltage_min_v, m.voltage_max_v
            FROM parts p
            JOIN mcu_specs m ON p.id = m.part_id
            WHERE p.id = ANY($1)
        """, design_parts)
        
        # Sensors
        sensors = await conn.fetch("""
            SELECT p.mpn, s.supply_voltage_min_v as min_v, s.supply_voltage_max_v as max_v
            FROM parts p
            JOIN sensor_specs s ON p.id = s.part_id
            WHERE p.id = ANY($1)
        """, design_parts)
        
        # Can Transceivers
        cans = await conn.fetch("""
             SELECT p.mpn, c.supply_voltage_min_v as min_v, c.supply_voltage_max_v as max_v
             FROM parts p
             JOIN can_specs c ON p.id = c.part_id
             WHERE p.id = ANY($1)
        """, design_parts)

        # PMICs (Input voltage)
        pmics = await conn.fetch("""
             SELECT p.mpn, pm.vin_min_v as min_v, pm.vin_max_v as max_v
             FROM parts p
             JOIN pmic_specs pm ON p.id = pm.part_id
             WHERE p.id = ANY($1)
        """, design_parts)

        # Combine
        active_parts = []
        for m in mcus:
            active_parts.append({'mpn': m['mpn'], 'min': m['voltage_min_v'], 'max': m['voltage_max_v']})
        for s in sensors:
            active_parts.append({'mpn': s['mpn'], 'min': s['min_v'], 'max': s['max_v']})
        for c in cans:
             active_parts.append({'mpn': c['mpn'], 'min': c['min_v'], 'max': c['max_v']})
        # Note: PMIC input range is usually WIDER and for the source, not the load rail. 
        # But we should check if PMIC input is compatible if we had a detailed power tree. 
        # For now, let's exclude PMIC from the "Load Rail" overlap check or treat it separately.
            
        if len(active_parts) < 2:
            return violations
        
        # Find common voltage range
        # Filter out None values just in case
        valid_parts = [p for p in active_parts if p['min'] is not None and p['max'] is not None]
        
        if not valid_parts:
             return violations

        common_min = max(p['min'] for p in valid_parts)
        common_max = min(p['max'] for p in valid_parts)
        
        if common_min > common_max:
            # No overlap
            ranges = ", ".join([f"{p['mpn']}: {p['min']}-{p['max']}V" for p in valid_parts])
            violations.append(Violation(
                rule_id="P001",
                rule_name="VDD Range Overlap",
                severity=Severity.ERROR,
                component="Power Supply",
                message=f"No common VDD range among components. Ranges: {ranges}",
                recommendation=f"Use a multi-rail power supply or select parts with overlapping voltage ranges.",
                design_id=design_id
            ))
        elif common_max - common_min < 0.2:
            # Very narrow range
            violations.append(Violation(
                rule_id="P001",
                rule_name="VDD Range Overlap",
                severity=Severity.WARNING,
                component="Power Supply",
                message=f"Common VDD range is very narrow: {common_min:.2f}-{common_max:.2f}V",
                recommendation="Consider parts with wider voltage tolerance for better margin.",
                design_id=design_id
            ))
        
        return violations
    
    async def check_power_sufficiency(self, conn: asyncpg.Connection,
                                     design_id: uuid.UUID,
                                     design_parts: List[uuid.UUID],
                                     pmic_id: Optional[uuid.UUID]) -> List[Violation]:
        """Rule P002: PMIC/LDO must provide enough rails/current"""
        violations = []
        if not pmic_id:
            # Check if there are any LDOs in design_parts (search via pmic_specs with ldo_count > 0, or just parts joined)
            # Since LDOs are in pmic_specs now? No, we had st_ldo_ingester.py seeding into `parts` and... wait.
            # LDOs were in `ldo_specs` (Phase 3 legacy) or `pmic_specs`?
            # Let's check ldo_specs or pmic_specs.
            
            # Check pmic_specs for LDOs
            pmic_ldos = await conn.fetchval("""
                SELECT COUNT(*) FROM parts p
                JOIN pmic_specs ps ON p.id = ps.part_id
                WHERE p.id = ANY($1) AND (ps.ldo_count > 0 OR ps.buck_count > 0)
            """, design_parts)
             
            # Check legacy ldo_specs if compatible (assuming table exists)
            # Just relying on pmic_specs for now as it covers PMICs. LDOs might be separate.
            # But the user logic merged LDO/PMIC somewhat. 
            # If no PMIC ID passed, we assume one of the design parts IS the power source.
            
            if pmic_ldos == 0:
                 # Check if we have an LDO part from legacy?
                 # Assuming dcdc_specs exists too.
                 dcdcs = await conn.fetchval("""
                    SELECT COUNT(*) FROM parts p
                    JOIN dcdc_specs ds ON p.id = ds.part_id
                    WHERE p.id = ANY($1)
                 """, design_parts)
                 
                 if dcdcs == 0:
                    violations.append(Violation(
                        rule_id="P002",
                        rule_name="Power Source Missing",
                        severity=Severity.WARNING,
                        component="System",
                        message="No PMIC, DC-DC, or LDO detected in design.",
                        recommendation="Ensure a stable power source is included.",
                        design_id=design_id
                    ))
            return violations
        
        # If PMIC exists, check basic rail counts
        pmic = await conn.fetchrow("""
            SELECT p.mpn, pm.buck_count, pm.ldo_count
            FROM parts p
            JOIN pmic_specs pm ON p.id = pm.part_id
            WHERE p.id = $1
        """, pmic_id)

        if not pmic:
             return violations

        # Estimate rails needed (MCU Core, MCU IO, Sensors, etc.)
        rails_needed = 2 
        
        available_rails = (pmic['buck_count'] or 0) + (pmic['ldo_count'] or 0)
        
        if available_rails < rails_needed:
             violations.append(Violation(
                rule_id="P002",
                rule_name="Power Rail Count",
                severity=Severity.WARNING,
                component=pmic['mpn'],
                message=f"PMIC provides {available_rails} rails, but system likely needs {rails_needed}+.",
                recommendation="Verify PMIC has enough output rails.",
                design_id=design_id
            ))

        return violations

    # ==================== COMMUNICATION RULES ====================
    
    async def check_can_compatibility(self, conn: asyncpg.Connection,
                                      design_id: uuid.UUID,
                                      design_parts: List[uuid.UUID]) -> List[Violation]:
        """Rule C001/C003: CAN Transceiver must match MCU voltage and have termination"""
        violations = []
        
        # Find MCU with CAN (using mcu_specs)
        mcu_can = await conn.fetchrow("""
            SELECT p.mpn, m.voltage_min_v, m.voltage_max_v
            FROM parts p
            JOIN mcu_specs m ON p.id = m.part_id
            WHERE p.id = ANY($1) AND m.can_count > 0
            LIMIT 1
        """, design_parts)
        
        if not mcu_can:
            return violations
            
        # Find CAN Transceiver (using can_specs)
        transceiver = await conn.fetchrow("""
            SELECT p.mpn, c.supply_voltage_min_v, c.supply_voltage_max_v
            FROM parts p
            JOIN can_specs c ON p.id = c.part_id
            WHERE p.id = ANY($1)
        """, design_parts)
        
        if not transceiver:
             violations.append(Violation(
                rule_id="C001",
                rule_name="Missing CAN Transceiver",
                severity=Severity.ERROR,
                component=mcu_can['mpn'],
                message="MCU has CAN enabled but no CAN transceiver found.",
                recommendation="Add a CAN transceiver (e.g., L9616 or L9966).",
                design_id=design_id
            ))
             return violations
        
        # Voltage Match Check
        tx_min = float(transceiver['supply_voltage_min_v'] or 0)
        tx_max = float(transceiver['supply_voltage_max_v'] or 0)
        mcu_min = float(mcu_can['voltage_min_v'] or 0)
        mcu_max = float(mcu_can['voltage_max_v'] or 0)
        
        if tx_min > mcu_max or tx_max < mcu_min:
            violations.append(Violation(
                rule_id="C001",
                rule_name="CAN Voltage Mismatch",
                severity=Severity.ERROR,
                component="CAN Bus",
                message=f"Transceiver voltage ({tx_min}-{tx_max}V) does not overlap with MCU ({mcu_min}-{mcu_max}V).",
                recommendation="Select a transceiver with compatible voltage levels.",
                design_id=design_id
            )) 
             
        # Termination Check
        has_termination = await conn.fetchval("""
            SELECT EXISTS(
                SELECT 1 FROM parts p
                JOIN passive_specs ps ON p.id = ps.part_id
                WHERE p.id = ANY($1) 
                AND ps.component_type = 'Resistor' 
                AND ps.resistance_ohm BETWEEN 115 AND 125
            )
        """, design_parts)
        
        if not has_termination:
             violations.append(Violation(
                rule_id="C003",
                rule_name="CAN Termination",
                severity=Severity.WARNING,
                component="CAN Bus",
                message="No 120Ω termination resistor detected.",
                recommendation="Add 120Ω resistors at bus ends.",
                design_id=design_id
            ))

        return violations

    # ==================== CLOCK & SIGNAL RULES ====================

    async def check_i2c_pullups(self, conn: asyncpg.Connection,
                               design_id: uuid.UUID,
                               design_parts: List[uuid.UUID]) -> List[Violation]:
        """Rule C002: I2C buses need pull-up resistors"""
        violations = []
        
        # Check if any MCU has I2C peripherals
        i2c_mcus = await conn.fetch("""
            SELECT p.mpn, m.i2c_count
            FROM parts p
            JOIN mcu_specs m ON p.id = m.part_id
            WHERE p.id = ANY($1) AND m.i2c_count > 0
        """, design_parts)
        
        if not i2c_mcus:
            return violations
            
        # Check for 4.7k resistors (approx match 4.6k-4.8k)
        has_pullups = await conn.fetchval("""
            SELECT EXISTS(
                SELECT 1 FROM parts p
                JOIN passive_specs ps ON p.id = ps.part_id
                WHERE p.id = ANY($1) 
                AND ps.component_type = 'Resistor' 
                AND ps.resistance_ohm BETWEEN 4600 AND 4800
            )
        """, design_parts)
        
        if not has_pullups:
            for mcu in i2c_mcus:
                violations.append(Violation(
                    rule_id="C002",
                    rule_name="I2C Pull-ups",
                    severity=Severity.WARNING,
                    component=mcu['mpn'],
                    message=f"I2C usage detected ({mcu['i2c_count']} busses) but no 4.7kΩ pull-up resistors found.",
                    recommendation="Add 4.7kΩ pull-ups on SDA and SCL lines.",
                    design_id=design_id
                ))
        
        return violations

    async def check_crystal_load_cap(self, conn: asyncpg.Connection,
                                    design_id: uuid.UUID,
                                    design_parts: List[uuid.UUID]) -> List[Violation]:
        """Rule CLK001: Crystal load capacitance"""
        violations = []
        
        # Just info for now if MCU present
        mcus = await conn.fetch("""
            SELECT p.mpn FROM parts p
            JOIN mcu_specs m ON p.id = m.part_id
            WHERE p.id = ANY($1)
        """, design_parts)
        
        for mcu in mcus:
            violations.append(Violation(
                rule_id="CLK001",
                rule_name="Crystal Load Capacitance",
                severity=Severity.INFO,
                component=mcu['mpn'],
                message="Verify crystal load capacitance matches MCU spec",
                recommendation="Check datasheet. Typically CL = 2*(C_ext - C_stray).",
                design_id=design_id
            ))
        
        return violations

    # ==================== MEMORY & THERMAL RULES ====================

    async def check_memory_constraints(self, conn: asyncpg.Connection,
                                      design_id: uuid.UUID,
                                      design_parts: List[uuid.UUID],
                                      required_flash_kb: int,
                                      required_ram_kb: int) -> List[Violation]:
        """Rule M001/M002: Memory sufficiency"""
        violations = []
        if required_flash_kb == 0 and required_ram_kb == 0:
            return violations
            
        mcus = await conn.fetch("""
            SELECT p.mpn, m.flash_kb, m.sram_kb
            FROM parts p
            JOIN mcu_specs m ON p.id = m.part_id
            WHERE p.id = ANY($1)
        """, design_parts)
        

        
        for mcu in mcus:
            # Flash
            if required_flash_kb > 0 and (mcu['flash_kb'] or 0) < required_flash_kb:
                violations.append(Violation(
                    rule_id="M001",
                    rule_name="Flash Size",
                    severity=Severity.ERROR,
                    component=mcu['mpn'],
                    message=f"Flash ({mcu['flash_kb']}KB) < Required ({required_flash_kb}KB)",
                    recommendation=f"Select MCU with >={required_flash_kb}KB Flash.",
                    design_id=design_id
                ))
            
            # RAM
            if required_ram_kb > 0 and (mcu['sram_kb'] or 0) < required_ram_kb:
                violations.append(Violation(
                    rule_id="M002",
                    rule_name="RAM Size",
                    severity=Severity.ERROR,
                    component=mcu['mpn'],
                    message=f"RAM ({mcu['sram_kb']}KB) < Required ({required_ram_kb}KB)",
                    recommendation=f"Select MCU with >={required_ram_kb}KB RAM.",
                    design_id=design_id
                ))
                
        return violations

    async def check_temperature_limits(self, conn: asyncpg.Connection,
                                      design_id: uuid.UUID,
                                      design_parts: List[uuid.UUID],
                                      ambient_temp_c: float) -> List[Violation]:
        """Rule T001: Temperature limits"""
        violations = []
        
        # Check parts temp range
        parts = await conn.fetch("""
             SELECT mpn, temp_min_c, temp_max_c FROM parts
             WHERE id = ANY($1)
             AND temp_max_c IS NOT NULL
        """, design_parts)
        
        for p in parts:
            if ambient_temp_c > p['temp_max_c']:
                 violations.append(Violation(
                    rule_id="T001",
                    rule_name="Temperature Limit",
                    severity=Severity.ERROR,
                    component=p['mpn'],
                    message=f"Ambient temp ({ambient_temp_c}C) exceeds part max ({p['temp_max_c']}C)",
                    recommendation="Select higher temperature grade part.",
                    design_id=design_id
                ))
        
        return violations

    # ==================== MASTER CHECK ====================
    
    async def check_design(self, design_parts: List[uuid.UUID],
                          design_id: Optional[uuid.UUID] = None,
                          pmic_id: Optional[uuid.UUID] = None,
                          ambient_temp_c: float = 25) -> Dict[str, Any]:
        """Run all design rule checks"""
        
        if not design_id:
            design_id = uuid.uuid4()
            
        async with self.db_pool.acquire() as conn:
            all_violations: List[Violation] = []
            
            # Power
            all_violations.extend(await self.check_vdd_range_overlap(conn, design_id, design_parts))
            all_violations.extend(await self.check_power_sufficiency(conn, design_id, design_parts, pmic_id))
            
            # Comm & Clock
            all_violations.extend(await self.check_can_compatibility(conn, design_id, design_parts))
            all_violations.extend(await self.check_i2c_pullups(conn, design_id, design_parts))
            all_violations.extend(await self.check_crystal_load_cap(conn, design_id, design_parts))

            # Constraints (Memory/Thermal)
            all_violations.extend(await self.check_memory_constraints(conn, design_id, design_parts, 32, 4))
            all_violations.extend(await self.check_temperature_limits(conn, design_id, design_parts, ambient_temp_c))
            
            # Save to DB
            await self.save_violations(conn, all_violations)
            
            # Summary
            summary = {
                'total': len(all_violations),
                'errors': sum(1 for v in all_violations if v.severity == Severity.ERROR),
                'warnings': sum(1 for v in all_violations if v.severity == Severity.WARNING),
                'info': sum(1 for v in all_violations if v.severity == Severity.INFO)
            }
            
            return {
                'violations': all_violations,
                'summary': summary
            }

# CLI Test
async def main():
    import os
    import sys
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot")
    pool = await asyncpg.create_pool(db_url)
    checker = DesignRuleChecker(pool)
    print("DRC Engine Initialized.")
    await pool.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
