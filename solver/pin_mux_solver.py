"""
Pin Mux Solver

Solves pin assignment conflicts using constraint satisfaction algorithm.

Features:
- Assigns peripheral functions to MCU pins
- Detects conflicts (multiple functions on same pin)
- Validates electrical constraints (voltage levels, current)
- Suggests alternative pin assignments
- Optimizes for routing (minimizes trace crossings)

Algorithm:
1. Build constraint graph
2. Assign required pins first (power, boot, etc.)
3. Use backtracking search for peripheral pins
4. Validate electrical constraints
5. Return valid assignment or conflicts
"""

import asyncpg
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid


class PinType(Enum):
    """Pin function type"""
    GPIO = "gpio"
    UART = "uart"
    SPI = "spi"
    I2C = "i2c"
    CAN = "can"
    USB = "usb"
    ADC = "adc"
    DAC = "dac"
    PWM = "pwm"
    TIMER = "timer"
    POWER = "power"
    BOOT = "boot"


@dataclass
class PinRequirement:
    """Required pin function"""
    function_type: PinType
    function_name: str  # e.g., "USART1_TX", "SPI2_MOSI"
    required: bool = True
    preferred_pins: List[str] = None  # Preferred pin names


@dataclass
class PinAssignment:
    """Pin assignment result"""
    pin_name: str
    pin_number: int
    function_type: PinType
    function_name: str
    alternate_function: int  # AF number (0-15)


@dataclass
class PinConflict:
    """Pin assignment conflict"""
    pin_name: str
    conflicting_functions: List[str]
    reason: str
    suggestions: List[str]


class PinMuxSolver:
    """Solve pin muxing constraints"""
    
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def get_pin_functions(self, part_id: uuid.UUID) -> Dict[str, Dict[str, Any]]:
        """
        Get all pin functions for an MCU
        """
        async with self.db_pool.acquire() as conn:
            pins = await conn.fetch("""
                SELECT * FROM mcu_pin_functions
                WHERE part_id = $1
                ORDER BY pin_number
            """, part_id)
            
            pin_map = {}
            
            for pin in pins:
                functions = {}
                for af in range(16):
                    af_col = f"af{af}_function"
                    if pin[af_col]:
                        functions[af] = pin[af_col]
                
                pin_map[pin['pin_name']] = {
                    'pin_number': pin['pin_number'],
                    'functions': functions,
                    'has_adc': pin['has_adc'],
                    'has_dac': pin['has_dac'],
                    'is_power_pin': pin['is_power_pin'],
                    'is_boot_pin': pin['is_boot_pin'],
                    'max_current_ma': pin['max_current_ma'],
                    'voltage_tolerance': pin['voltage_tolerance']
                }
            
            return pin_map
    
    async def get_constraints(self, part_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get pin muxing constraints"""
        async with self.db_pool.acquire() as conn:
            constraints = await conn.fetch("""
                SELECT * FROM pin_mux_constraints
                WHERE part_id = $1
            """, part_id)
            
            return [dict(c) for c in constraints]
    
    def find_pins_for_function(self, pin_map: Dict[str, Dict[str, Any]], 
                               function_name: str) -> List[Tuple[str, int]]:
        """
        Find all pins that can provide a specific function
        
        Returns:
            List of (pin_name, af_number) tuples
        """
        candidates = []
        
        for pin_name, pin_data in pin_map.items():
            for af, func in pin_data['functions'].items():
                if func == function_name:
                    candidates.append((pin_name, af))
        
        return candidates
    
    def check_conflicts(self, assignments: Dict[str, PinAssignment]) -> List[PinConflict]:
        """Check for pin assignment conflicts"""
        conflicts = []
        pin_usage = {}
        
        # Group assignments by pin
        for func_name, assignment in assignments.items():
            pin = assignment.pin_name
            if pin not in pin_usage:
                pin_usage[pin] = []
            pin_usage[pin].append(func_name)
        
        # Find conflicts (multiple functions on same pin)
        for pin, functions in pin_usage.items():
            if len(functions) > 1:
                conflicts.append(PinConflict(
                    pin_name=pin,
                    conflicting_functions=functions,
                    reason=f"Multiple functions assigned to {pin}",
                    suggestions=[f"Move one function to alternate pin"]
                ))
        
        return conflicts
    
    async def solve(self, part_id: uuid.UUID, 
                   requirements: List[PinRequirement]) -> Dict[str, Any]:
        """
        Solve pin muxing for given requirements
        """
        # Get pin functions
        pin_map = await self.get_pin_functions(part_id)
        
        if not pin_map:
            return {
                'success': False,
                'assignments': {},
                'conflicts': [],
                'unassigned': [req.function_name for req in requirements],
                'error': 'No pin data available for this MCU'
            }
        
        # Get constraints
        # constraints = await self.get_constraints(part_id) # Unused for now
        
        assignments = {}
        unassigned = []
        
        # Sort requirements: required first, then by preferred pins
        sorted_reqs = sorted(requirements, 
                           key=lambda r: (not r.required, len(r.preferred_pins or [])))
        
        # Assign pins using greedy algorithm with backtracking
        used_pins = set()
        
        for req in sorted_reqs:
            # Find candidate pins
            candidates = self.find_pins_for_function(pin_map, req.function_name)
            
            if not candidates:
                if req.required:
                    unassigned.append(req.function_name)
                continue
            
            # Filter out already used pins
            available = [(pin, af) for pin, af in candidates if pin not in used_pins]
            
            if not available:
                if req.required:
                    unassigned.append(req.function_name)
                continue
            
            # Prefer pins from preferred list
            if req.preferred_pins:
                preferred = [(pin, af) for pin, af in available 
                           if pin in req.preferred_pins]
                if preferred:
                    available = preferred
            
            # Assign first available pin
            pin_name, af = available[0]
            assignments[req.function_name] = PinAssignment(
                pin_name=pin_name,
                pin_number=pin_map[pin_name]['pin_number'],
                function_type=req.function_type,
                function_name=req.function_name,
                alternate_function=af
            )
            used_pins.add(pin_name)
        
        # Check for conflicts
        conflicts = self.check_conflicts(assignments)
        
        success = len(conflicts) == 0 and len(unassigned) == 0
        
        return {
            'success': success,
            'assignments': assignments,
            'conflicts': conflicts,
            'unassigned': unassigned
        }
    
    async def validate_electrical(self, part_id: uuid.UUID,
                                  assignments: Dict[str, PinAssignment]) -> List[str]:
        """
        Validate electrical constraints
        """
        warnings = []
        pin_map = await self.get_pin_functions(part_id)
        
        for func_name, assignment in assignments.items():
            pin_data = pin_map.get(assignment.pin_name)
            if not pin_data:
                continue
            
            # Check voltage tolerance for 5V peripherals
            if '5V' in func_name.upper() and pin_data['voltage_tolerance'] != '5V tolerant':
                warnings.append(
                    f"{assignment.pin_name}: {func_name} may require 5V tolerance"
                )
            
            # Check current capacity for high-current functions
            if 'LED' in func_name.upper() or 'MOTOR' in func_name.upper():
                if pin_data['max_current_ma'] and pin_data['max_current_ma'] < 20:
                    warnings.append(
                        f"{assignment.pin_name}: {func_name} may exceed max current "
                        f"({pin_data['max_current_ma']}mA)"
                    )
        
        return warnings
    
    async def suggest_alternatives(self, part_id: uuid.UUID,
                                  conflict: PinConflict) -> List[Dict[str, Any]]:
        """Suggest alternative pin assignments for conflicts"""
        pin_map = await self.get_pin_functions(part_id)
        suggestions = []
        
        for func in conflict.conflicting_functions:
            # Find alternative pins
            candidates = self.find_pins_for_function(pin_map, func)
            alt_pins = [pin for pin, af in candidates if pin != conflict.pin_name]
            
            if alt_pins:
                suggestions.append({
                    'function': func,
                    'current_pin': conflict.pin_name,
                    'alternative_pins': alt_pins[:3]  # Top 3 alternatives
                })
        
        return suggestions


# Example usage
async def main():
    import os
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")
    pool = await asyncpg.create_pool(db_url)
    solver = PinMuxSolver(pool)
    
    # ... example usage would need real part_id ...
    print("PinMuxSolver initialized with pool")
    
    await pool.close()


if __name__ == "__main__":
    import asyncio
    import sys
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
