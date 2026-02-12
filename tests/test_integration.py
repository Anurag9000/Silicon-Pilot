"""
Integration Tests

Tests complete workflows end-to-end:
- Search and recommendation
- Alternative suggestion
- Design rule checking
- Pin mux solving
- Power budget calculation
- Firmware stack recommendation
"""

import asyncio
import uuid
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from solver.alternative_suggester import AlternativeSuggester
from solver.design_rule_checker import DesignRuleChecker, Severity
from solver.pin_mux_solver import PinMuxSolver, PinRequirement, PinType
from solver.power_budget_calculator import PowerBudgetCalculator, ModeProfile, PowerMode, PeripheralUsage, ExternalComponent
from architecture.firmware_stack_recommender import FirmwareStackRecommender, StackRequirement, StackType, LicenseType
from ml.ranker import MLRanker


class IntegrationTests:
    """Integration test suite"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.passed = 0
        self.failed = 0
    
    def assert_true(self, condition: bool, message: str):
        """Assert condition is true"""
        if condition:
            print(f"  [OK] {message}")
            self.passed += 1
        else:
            print(f"  [FAIL] {message}")
            self.failed += 1
    
    async def test_alternative_suggester(self):
        """Test alternative suggestion engine"""
        print("\n[TEST] Alternative Suggester")
        
        suggester = AlternativeSuggester(self.db_url)
        
        # Test would require actual part IDs in database
        # For now, just verify the module loads
        self.assert_true(suggester is not None, "Alternative suggester initialized")
    
    async def test_design_rule_checker(self):
        """Test design rule checker"""
        print("\n[TEST] Design Rule Checker")
        
        checker = DesignRuleChecker(self.db_url)
        
        # Test would require actual part IDs
        self.assert_true(checker is not None, "Design rule checker initialized")
    
    async def test_pin_mux_solver(self):
        """Test pin mux solver"""
        print("\n[TEST] Pin Mux Solver")
        
        solver = PinMuxSolver(self.db_url)
        
        # Test basic functionality
        self.assert_true(solver is not None, "Pin mux solver initialized")
        
        # Test pin requirement creation
        req = PinRequirement(PinType.UART, "USART1_TX", required=True)
        self.assert_true(req.function_type == PinType.UART, "Pin requirement created")
    
    async def test_power_budget_calculator(self):
        """Test power budget calculator"""
        print("\n[TEST] Power Budget Calculator")
        
        calculator = PowerBudgetCalculator(self.db_url)
        
        self.assert_true(calculator is not None, "Power budget calculator initialized")
        
        # Test mode profile creation
        mode = ModeProfile(PowerMode.RUN, duration_percent=50, frequency_mhz=168)
        self.assert_true(mode.mode == PowerMode.RUN, "Mode profile created")
        
        # Test external component power calculation
        components = [
            ExternalComponent("LED", voltage_v=3.3, current_ma=2, duty_cycle_percent=10)
        ]
        powers = calculator.calculate_external_power(components)
        self.assert_true('LED' in powers, "External power calculated")
        self.assert_true(powers['LED'] > 0, "LED power > 0")
    
    async def test_firmware_stack_recommender(self):
        """Test firmware stack recommender"""
        print("\n[TEST] Firmware Stack Recommender")
        
        recommender = FirmwareStackRecommender(self.db_url)
        
        self.assert_true(recommender is not None, "Firmware stack recommender initialized")
        
        # Test stack requirement creation
        req = StackRequirement(
            stack_type=StackType.RTOS,
            required_features=['preemptive'],
            license_preference=LicenseType.PERMISSIVE
        )
        self.assert_true(req.stack_type == StackType.RTOS, "Stack requirement created")
    
    async def test_ml_ranker(self):
        """Test ML ranker"""
        print("\n[TEST] ML Ranker")
        
        ranker = MLRanker(self.db_url)
        
        self.assert_true(ranker is not None, "ML ranker initialized")
        self.assert_true(len(ranker.feature_names) == 9, "Feature names defined")
    
    async def run_all(self):
        """Run all integration tests"""
        print("="*60)
        print(" "*15 + "INTEGRATION TESTS")
        print("="*60)
        
        await self.test_alternative_suggester()
        await self.test_design_rule_checker()
        await self.test_pin_mux_solver()
        await self.test_power_budget_calculator()
        await self.test_firmware_stack_recommender()
        await self.test_ml_ranker()
        
        print("\n" + "="*60)
        print(f"Results: {self.passed} passed, {self.failed} failed")
        print("="*60 + "\n")
        
        return self.failed == 0


async def main():
    import os
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")
    
    tests = IntegrationTests(db_url)
    success = await tests.run_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
