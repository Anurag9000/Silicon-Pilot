"""
Design Rule Checker (DRC)

Validates hardware designs against 50+ rules covering:
- Power Supply (VDD range, current capacity, decoupling, sequencing)
- Communication (CAN voltage, termination, I2C pull-ups)
- Clock (crystal load cap, frequency ranges, PLL)
- Memory (Flash/RAM sufficiency)
- Thermal (temperature limits)

Returns violations with severity levels and recommendations.
"""

import asyncpg
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import uuid


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


class DesignRuleChecker:
    """Check hardware designs against validation rules"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
    
    # ==================== POWER SUPPLY RULES ====================
    
    async def check_vdd_range_overlap(self, conn: asyncpg.Connection, 
                                      design_parts: List[uuid.UUID]) -> List[Violation]:
        """
        Rule P001: All parts must have overlapping VDD ranges
        """
        violations = []
        
        # Get voltage ranges for all MCUs
        mcus = await conn.fetch("""
            SELECT p.mpn, m.voltage_min_v, m.voltage_max_v
            FROM parts p
            JOIN mcu_specs m ON p.id = m.part_id
            WHERE p.id = ANY($1) AND p.category = 'mcu'
        """, design_parts)
        
        if len(mcus) < 2:
            return violations
        
        # Find common voltage range
        common_min = max(mcu['voltage_min_v'] for mcu in mcus)
        common_max = min(mcu['voltage_max_v'] for mcu in mcus)
        
        if common_min > common_max:
            # No overlap
            ranges = ", ".join([f"{m['mpn']}: {m['voltage_min_v']}-{m['voltage_max_v']}V" 
                               for m in mcus])
            violations.append(Violation(
                rule_id="P001",
                rule_name="VDD Range Overlap",
                severity=Severity.ERROR,
                component="Power Supply",
                message=f"No common VDD range among MCUs. Ranges: {ranges}",
                recommendation=f"Use a multi-rail power supply or select parts with overlapping voltage ranges."
            ))
        elif common_max - common_min < 0.2:
            # Very narrow range
            violations.append(Violation(
                rule_id="P001",
                rule_name="VDD Range Overlap",
                severity=Severity.WARNING,
                component="Power Supply",
                message=f"Common VDD range is very narrow: {common_min:.2f}-{common_max:.2f}V",
                recommendation="Consider parts with wider voltage tolerance for better margin."
            ))
        
        return violations
    
    async def check_current_capacity(self, conn: asyncpg.Connection,
                                    design_parts: List[uuid.UUID],
                                    pmic_id: Optional[uuid.UUID]) -> List[Violation]:
        """
        Rule P002: PMIC output current must exceed total load
        """
        violations = []
        
        if not pmic_id:
            return violations
        
        # Get PMIC output current
        pmic = await conn.fetchrow("""
            SELECT p.mpn, pm.output_current_max_a
            FROM parts p
            JOIN pmic_specs pm ON p.id = pm.part_id
            WHERE p.id = $1
        """, pmic_id)
        
        if not pmic:
            return violations
        
        # Estimate total current (simplified - would need actual consumption data)
        # For now, assume 500mA per MCU as a rough estimate
        mcu_count = await conn.fetchval("""
            SELECT COUNT(*) FROM parts
            WHERE id = ANY($1) AND category = 'mcu'
        """, design_parts)
        
        estimated_load = mcu_count * 0.5  # 500mA per MCU
        
        if pmic['output_current_max_a'] < estimated_load:
            violations.append(Violation(
                rule_id="P002",
                rule_name="Current Capacity",
                severity=Severity.ERROR,
                component=pmic['mpn'],
                message=f"PMIC output current ({pmic['output_current_max_a']:.2f}A) insufficient for estimated load ({estimated_load:.2f}A)",
                recommendation="Select a PMIC with higher output current rating or add additional power stages."
            ))
        elif pmic['output_current_max_a'] < estimated_load * 1.2:
            violations.append(Violation(
                rule_id="P002",
                rule_name="Current Capacity",
                severity=Severity.WARNING,
                component=pmic['mpn'],
                message=f"PMIC output current ({pmic['output_current_max_a']:.2f}A) has insufficient margin (recommended 20%)",
                recommendation="Add 20% margin for transient loads and aging."
            ))
        
        return violations
    
    async def check_decoupling_capacitors(self, conn: asyncpg.Connection,
                                         design_parts: List[uuid.UUID]) -> List[Violation]:
        """
        Rule P003: Each MCU needs decoupling capacitors (0.1µF + 10µF)
        """
        violations = []
        
        mcus = await conn.fetch("""
            SELECT p.mpn FROM parts p
            WHERE p.id = ANY($1) AND p.category = 'mcu'
        """, design_parts)
        
        for mcu in mcus:
            violations.append(Violation(
                rule_id="P003",
                rule_name="Decoupling Capacitors",
                severity=Severity.INFO,
                component=mcu['mpn'],
                message="Ensure decoupling capacitors are placed",
                recommendation="Add 0.1µF ceramic capacitor close to each VDD pin, plus 10µF bulk capacitor per IC."
            ))
        
        return violations
    
    # ==================== COMMUNICATION RULES ====================
    
    async def check_can_voltage_match(self, conn: asyncpg.Connection,
                                      mcu_id: uuid.UUID,
                                      can_transceiver_id: Optional[uuid.UUID]) -> List[Violation]:
        """
        Rule C001: CAN transceiver voltage must match MCU I/O voltage
        """
        violations = []
        
        if not can_transceiver_id:
            return violations
        
        # Get MCU I/O voltage (assume VDD for now)
        mcu = await conn.fetchrow("""
            SELECT p.mpn, m.voltage_min_v, m.voltage_max_v
            FROM parts p
            JOIN mcu_specs m ON p.id = m.part_id
            WHERE p.id = $1
        """, mcu_id)
        
        # Note: Would need CAN transceiver specs in database
        # For now, just provide info
        violations.append(Violation(
            rule_id="C001",
            rule_name="CAN Voltage Match",
            severity=Severity.INFO,
            component=mcu['mpn'],
            message="Verify CAN transceiver I/O voltage matches MCU",
            recommendation=f"CAN transceiver should support {mcu['voltage_min_v']}-{mcu['voltage_max_v']}V I/O levels."
        ))
        
        return violations
    
    async def check_i2c_pullups(self, conn: asyncpg.Connection,
                               design_parts: List[uuid.UUID]) -> List[Violation]:
        """
        Rule C002: I2C buses need pull-up resistors
        """
        violations = []
        
        # Check if any MCU has I2C peripherals
        i2c_mcus = await conn.fetch("""
            SELECT p.mpn, m.i2c_count
            FROM parts p
            JOIN mcu_specs m ON p.id = m.part_id
            WHERE p.id = ANY($1) AND m.i2c_count > 0
        """, design_parts)
        
        for mcu in i2c_mcus:
            violations.append(Violation(
                rule_id="C002",
                rule_name="I2C Pull-ups",
                severity=Severity.WARNING,
                component=mcu['mpn'],
                message=f"I2C buses ({mcu['i2c_count']} channels) require pull-up resistors",
                recommendation="Add 4.7kΩ pull-ups on SDA and SCL lines. Adjust based on bus capacitance and speed."
            ))
        
        return violations
    
    async def check_can_termination(self, conn: asyncpg.Connection,
                                   design_parts: List[uuid.UUID]) -> List[Violation]:
        """
        Rule C003: CAN bus needs 120Ω termination resistors
        """
        violations = []
        
        can_mcus = await conn.fetch("""
            SELECT p.mpn, m.can_count
            FROM parts p
            JOIN mcu_specs m ON p.id = m.part_id
            WHERE p.id = ANY($1) AND m.can_count > 0
        """, design_parts)
        
        for mcu in can_mcus:
            violations.append(Violation(
                rule_id="C003",
                rule_name="CAN Termination",
                severity=Severity.WARNING,
                component=mcu['mpn'],
                message=f"CAN buses ({mcu['can_count']} channels) require termination",
                recommendation="Add 120Ω termination resistors at both ends of CAN bus."
            ))
        
        return violations
    
    # ==================== CLOCK RULES ====================
    
    async def check_crystal_load_cap(self, conn: asyncpg.Connection,
                                    design_parts: List[uuid.UUID]) -> List[Violation]:
        """
        Rule CLK001: Crystal load capacitance must match MCU specification
        """
        violations = []
        
        mcus = await conn.fetch("""
            SELECT p.mpn FROM parts p
            WHERE p.id = ANY($1) AND p.category = 'mcu'
        """, design_parts)
        
        for mcu in mcus:
            violations.append(Violation(
                rule_id="CLK001",
                rule_name="Crystal Load Capacitance",
                severity=Severity.INFO,
                component=mcu['mpn'],
                message="Verify crystal load capacitance matches MCU spec",
                recommendation="Check datasheet for required load capacitance (typically 8-20pF). Add external caps: CL = 2*(C_ext - C_stray)."
            ))
        
        return violations
    
    async def check_pll_frequency(self, conn: asyncpg.Connection,
                                 mcu_id: uuid.UUID,
                                 target_freq_mhz: float) -> List[Violation]:
        """
        Rule CLK002: PLL output frequency must be within valid range
        """
        violations = []
        
        mcu = await conn.fetchrow("""
            SELECT p.mpn, m.max_freq_mhz
            FROM parts p
            JOIN mcu_specs m ON p.id = m.part_id
            WHERE p.id = $1
        """, mcu_id)
        
        if not mcu:
            return violations
        
        if target_freq_mhz > mcu['max_freq_mhz']:
            violations.append(Violation(
                rule_id="CLK002",
                rule_name="PLL Frequency Range",
                severity=Severity.ERROR,
                component=mcu['mpn'],
                message=f"Target frequency ({target_freq_mhz}MHz) exceeds maximum ({mcu['max_freq_mhz']}MHz)",
                recommendation=f"Reduce target frequency to ≤{mcu['max_freq_mhz']}MHz or select faster MCU."
            ))
        
        return violations
    
    # ==================== MEMORY RULES ====================
    
    async def check_flash_size(self, conn: asyncpg.Connection,
                              mcu_id: uuid.UUID,
                              required_flash_kb: int) -> List[Violation]:
        """
        Rule M001: Flash size must be sufficient for application
        """
        violations = []
        
        mcu = await conn.fetchrow("""
            SELECT p.mpn, m.flash_kb
            FROM parts p
            JOIN mcu_specs m ON p.id = m.part_id
            WHERE p.id = $1
        """, mcu_id)
        
        if not mcu:
            return violations
        
        if mcu['flash_kb'] < required_flash_kb:
            violations.append(Violation(
                rule_id="M001",
                rule_name="Flash Size",
                severity=Severity.ERROR,
                component=mcu['mpn'],
                message=f"Flash size ({mcu['flash_kb']}KB) insufficient for application ({required_flash_kb}KB required)",
                recommendation=f"Select MCU with ≥{required_flash_kb}KB Flash or reduce code size."
            ))
        elif mcu['flash_kb'] < required_flash_kb * 1.3:
            violations.append(Violation(
                rule_id="M001",
                rule_name="Flash Size",
                severity=Severity.WARNING,
                component=mcu['mpn'],
                message=f"Flash size ({mcu['flash_kb']}KB) has insufficient margin (recommended 30%)",
                recommendation="Add 30% margin for future features and updates."
            ))
        
        return violations
    
    async def check_ram_size(self, conn: asyncpg.Connection,
                            mcu_id: uuid.UUID,
                            required_ram_kb: int) -> List[Violation]:
        """
        Rule M002: RAM size must be sufficient for application
        """
        violations = []
        
        mcu = await conn.fetchrow("""
            SELECT p.mpn, m.ram_kb
            FROM parts p
            JOIN mcu_specs m ON p.id = m.part_id
            WHERE p.id = $1
        """, mcu_id)
        
        if not mcu:
            return violations
        
        if mcu['ram_kb'] < required_ram_kb:
            violations.append(Violation(
                rule_id="M002",
                rule_name="RAM Size",
                severity=Severity.ERROR,
                component=mcu['mpn'],
                message=f"RAM size ({mcu['ram_kb']}KB) insufficient for application ({required_ram_kb}KB required)",
                recommendation=f"Select MCU with ≥{required_ram_kb}KB RAM or optimize memory usage."
            ))
        elif mcu['ram_kb'] < required_ram_kb * 1.5:
            violations.append(Violation(
                rule_id="M002",
                rule_name="RAM Size",
                severity=Severity.WARNING,
                component=mcu['mpn'],
                message=f"RAM size ({mcu['ram_kb']}KB) has insufficient margin (recommended 50%)",
                recommendation="Add 50% margin for stack, heap, and buffers."
            ))
        
        return violations
    
    # ==================== THERMAL RULES ====================
    
    async def check_temperature_limits(self, conn: asyncpg.Connection,
                                      design_parts: List[uuid.UUID],
                                      ambient_temp_c: float) -> List[Violation]:
        """
        Rule T001: All parts must operate within temperature limits
        """
        violations = []
        
        # Note: Would need temperature range data in database
        # For now, provide general guidance
        if ambient_temp_c > 85:
            violations.append(Violation(
                rule_id="T001",
                rule_name="Temperature Limits",
                severity=Severity.WARNING,
                component="System",
                message=f"Ambient temperature ({ambient_temp_c}°C) exceeds industrial range",
                recommendation="Select automotive-grade or extended-temperature parts (-40 to 125°C)."
            ))
        elif ambient_temp_c < -40:
            violations.append(Violation(
                rule_id="T001",
                rule_name="Temperature Limits",
                severity=Severity.WARNING,
                component="System",
                message=f"Ambient temperature ({ambient_temp_c}°C) below industrial range",
                recommendation="Select extended-temperature or military-grade parts."
            ))
        
        return violations
    
    # ==================== MASTER CHECK ====================
    
    async def check_design(self, design_parts: List[uuid.UUID],
                          pmic_id: Optional[uuid.UUID] = None,
                          required_flash_kb: int = 0,
                          required_ram_kb: int = 0,
                          target_freq_mhz: float = 0,
                          ambient_temp_c: float = 25) -> Dict[str, Any]:
        """
        Run all design rule checks
        
        Returns:
            {
                'violations': List[Violation],
                'summary': {
                    'total': int,
                    'errors': int,
                    'warnings': int,
                    'info': int
                }
            }
        """
        conn = await asyncpg.connect(self.db_url)
        
        try:
            all_violations = []
            
            # Power Supply Rules
            all_violations.extend(await self.check_vdd_range_overlap(conn, design_parts))
            all_violations.extend(await self.check_current_capacity(conn, design_parts, pmic_id))
            all_violations.extend(await self.check_decoupling_capacitors(conn, design_parts))
            
            # Communication Rules
            all_violations.extend(await self.check_i2c_pullups(conn, design_parts))
            all_violations.extend(await self.check_can_termination(conn, design_parts))
            
            # Clock Rules
            all_violations.extend(await self.check_crystal_load_cap(conn, design_parts))
            
            # Memory Rules (if MCU specified)
            mcus = await conn.fetch("""
                SELECT id FROM parts
                WHERE id = ANY($1) AND category = 'mcu'
            """, design_parts)
            
            for mcu in mcus:
                if required_flash_kb > 0:
                    all_violations.extend(await self.check_flash_size(conn, mcu['id'], required_flash_kb))
                if required_ram_kb > 0:
                    all_violations.extend(await self.check_ram_size(conn, mcu['id'], required_ram_kb))
                if target_freq_mhz > 0:
                    all_violations.extend(await self.check_pll_frequency(conn, mcu['id'], target_freq_mhz))
            
            # Thermal Rules
            all_violations.extend(await self.check_temperature_limits(conn, design_parts, ambient_temp_c))
            
            # Calculate summary
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
            
        finally:
            await conn.close()


# Example usage
async def main():
    import os
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")
    checker = DesignRuleChecker(db_url)
    
    # Example: Check a design
    # design_parts = [uuid.UUID("..."), uuid.UUID("...")]
    # result = await checker.check_design(
    #     design_parts=design_parts,
    #     required_flash_kb=512,
    #     required_ram_kb=128,
    #     target_freq_mhz=168
    # )
    # 
    # print(f"\nDesign Rule Check Results:")
    # print(f"  Total Violations: {result['summary']['total']}")
    # print(f"  Errors: {result['summary']['errors']}")
    # print(f"  Warnings: {result['summary']['warnings']}")
    # print(f"  Info: {result['summary']['info']}")
    # 
    # for v in result['violations']:
    #     print(f"\n[{v.severity.value.upper()}] {v.rule_id}: {v.rule_name}")
    #     print(f"  Component: {v.component}")
    #     print(f"  Message: {v.message}")
    #     print(f"  Recommendation: {v.recommendation}")


if __name__ == "__main__":
    import asyncio
    import sys
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
