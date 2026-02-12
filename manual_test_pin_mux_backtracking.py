
import asyncio
import uuid
import asyncpg
from typing import List, Dict, Any
from solver.pin_mux_solver import PinMuxSolver, PinRequirement, PinType

# Mock DB Pool and Connection
class MockRecord(dict):
    def __getattr__(self, name):
        return self[name]

class MockConnection:
    def __init__(self, pin_data, constraints_data):
        self.pin_data = pin_data
        self.constraints_data = constraints_data

    async def fetch(self, query, *args):
        if "mcu_pin_functions" in query:
            return [MockRecord(x) for x in self.pin_data]
        elif "pin_mux_constraints" in query:
            return [MockRecord(x) for x in self.constraints_data]
        return []

    async def close(self):
        pass

class MockPool:
    def __init__(self, pin_data, constraints_data):
        self.pin_data = pin_data
        self.constraints_data = constraints_data

    def acquire(self):
        return self

    async def __aenter__(self):
        return MockConnection(self.pin_data, self.constraints_data)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

async def test_backtracking():
    print("Testing Backtracking Logic...")
    
    # Setup Data
    # Pins: 
    #   PA0: UART_TX (AF1), SPI_SCK (AF2)
    #   PA1: UART_TX (AF1)
    
    pin_data = [
        {
            "pin_name": "PA0", "pin_number": 1, 
            "af0_function": None, "af1_function": "UART_TX", "af2_function": "SPI_SCK", 
            "af3_function": None, "af4_function": None, "af5_function": None,
            "af6_function": None, "af7_function": None, "af8_function": None,
            "af9_function": None, "af10_function": None, "af11_function": None,
            "af12_function": None, "af13_function": None, "af14_function": None,
            "af15_function": None,
            "has_adc": False, "has_dac": False, "is_power_pin": False, "is_boot_pin": False,
            "max_current_ma": 20, "voltage_tolerance": "3.3V"
        },
        {
            "pin_name": "PA1", "pin_number": 2, 
            "af0_function": None, "af1_function": "UART_TX", "af2_function": None, 
            "af3_function": None, "af4_function": None, "af5_function": None,
            "af6_function": None, "af7_function": None, "af8_function": None,
            "af9_function": None, "af10_function": None, "af11_function": None,
            "af12_function": None, "af13_function": None, "af14_function": None,
            "af15_function": None,
            "has_adc": False, "has_dac": False, "is_power_pin": False, "is_boot_pin": False,
            "max_current_ma": 20, "voltage_tolerance": "3.3V"
        }
    ]
    constraints_data = [] # No constraints for this test
    
    pool = MockPool(pin_data, constraints_data)
    solver = PinMuxSolver(pool)
    
    # Scenario:
    # Req1: SPI_SCK (Only on PA0)
    # Req2: UART_TX (Preferred PA0, but can be PA1)
    
    # If Greedy processes Req2 first (e.g. if it has preferred pins and Req1 doesn't - wait, sorted by required first. Both required.)
    # Let's make Req2 have preferred_pins=["PA0"] so it might be processed after or before Req1 depending on sort stability or 
    # secondary sort key: len(preferred_pins).
    # key=lambda r: (not r.required, len(r.preferred_pins or []))
    # Req1: required=True, preferred=[] -> key=(0, 0)
    # Req2: required=True, preferred=["PA0"] -> key=(0, 1)
    # Checks: Req1 comes FIRST.
    
    # Wait, if Req1 comes first, it takes PA0. Then Req2 takes PA1. Success.
    # To force backtracking needs failure:
    # Req1: UART_TX (Preferred PA0). 
    # Req2: SPI_SCK (Only PA0).
    
    # Sorted:
    # Req2: preferred=[] -> key=(0, 0)
    # Req1: preferred=["PA0"] -> key=(0, 1)
    
    # Order: Req2 then Req1.
    # Req2 takes PA0 (SPI_SCK).
    # Req1 takes PA1 (UART_TX).
    # Success without backtracking.
    
    # We need a case where the FIRST choice of the FIRST processed item blocks the ONLY choice of the SECOND item.
    
    # Req1: UART_TX (Available on PA0, PA1). Preferred=[PA0].
    # Req2: SPI_SCK (Available on PA0).
    
    # Sort order?
    # Req2: preferred=[] -> (0,0)
    # Req1: preferred=[PA0] -> (0,1)
    # Req2 is processed first. It takes PA0.
    # Req1 needs UART. It sees PA0 is taken. It takes PA1.
    # Success.
    
    # Let's force strict order manually or rely on sort?
    # Let's make Req1 have NO preferred pins.
    # Req1: UART_TX. Candidates: PA0, PA1.
    # Req2: SPI_SCK. Candidates: PA0.
    
    # Sort: Both (0,0). Stability? Maybe Req1 comes first.
    # If Req1 comes first:
    # It picks PA0 (first in list/arbitrary).
    # Req2 needs PA0. Conflict!
    # Backtracking should undo Req1 assigned to PA0, try PA1.
    # Then Req2 gets PA0.
    
    req1 = PinRequirement(function_type=PinType.UART, function_name="UART_TX", required=True, preferred_pins=[])
    req2 = PinRequirement(function_type=PinType.SPI, function_name="SPI_SCK", required=True, preferred_pins=[])
    
    # Force Req1 to be processed first by passing it first? Python sort is stable.
    requirements = [req1, req2]
    
    result = await solver.solve(uuid.uuid4(), requirements)
    
    if result['success']:
        print("✓ Backtracking Test Passed!")
        # Verify assignments
        assignments = result['assignments']
        print(f"  UART_TX assigned to: {assignments['UART_TX'].pin_name}")
        print(f"  SPI_SCK assigned to: {assignments['SPI_SCK'].pin_name}")
        
        if assignments['SPI_SCK'].pin_name == "PA0" and assignments['UART_TX'].pin_name == "PA1":
            print("  Assignments correct.")
        else:
             print("  Assignments WRONG (Greedy?)")
    else:
        print("❌ Backtracking Test Failed!")
        print(result)

async def test_constraints():
    print("\nTesting Constraints Logic...")
    
    # Data: PA0 and PA1 are mutually exclusive
    # PA0: UART_TX
    # PA1: UART_RX
    
    pin_data = [
        {
            "pin_name": "PA0", "pin_number": 1, 
            "af0_function": None, "af1_function": "UART_TX", "af2_function": None, 
            "af3_function": None, "af4_function": None, "af5_function": None,
            "af6_function": None, "af7_function": None, "af8_function": None,
            "af9_function": None, "af10_function": None, "af11_function": None,
            "af12_function": None, "af13_function": None, "af14_function": None,
            "af15_function": None,
            "has_adc": False, "has_dac": False, "is_power_pin": False, "is_boot_pin": False,
            "max_current_ma": 20, "voltage_tolerance": "3.3V"
        },
        {
            "pin_name": "PA1", "pin_number": 2, 
            "af0_function": None, "af1_function": "UART_RX", "af2_function": None, 
            "af3_function": None, "af4_function": None, "af5_function": None,
            "af6_function": None, "af7_function": None, "af8_function": None,
            "af9_function": None, "af10_function": None, "af11_function": None,
            "af12_function": None, "af13_function": None, "af14_function": None,
            "af15_function": None,
            "has_adc": False, "has_dac": False, "is_power_pin": False, "is_boot_pin": False,
            "max_current_ma": 20, "voltage_tolerance": "3.3V"
        }
    ]
    
    constraints_data = [
        {
            "constraint_type": "exclusive",
            "pin_names": ["PA0", "PA1"],
            "description": "Cannot use both"
        }
    ]
    
    pool = MockPool(pin_data, constraints_data)
    solver = PinMuxSolver(pool)
    
    # Try to assign both
    req1 = PinRequirement(function_type=PinType.UART, function_name="UART_TX", required=True)
    req2 = PinRequirement(function_type=PinType.UART, function_name="UART_RX", required=True)
    
    requirements = [req1, req2]
    
    result = await solver.solve(uuid.uuid4(), requirements)
    
    if not result['success']:
        print("✓ Constraint Test Passed! (Correctly failed to assign conflicting pins)")
        print(f"  Unassigned: {result['unassigned']}")
    else:
        print("❌ Constraint Test Failed! (Assigned conflicting pins)")
        print(result['assignments'])

if __name__ == "__main__":
    asyncio.run(test_backtracking())
    # asyncio.run(test_constraints())
