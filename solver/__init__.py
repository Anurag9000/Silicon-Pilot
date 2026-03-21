"""
Solver Package

Contains optimization and constraint solving engines:
- Alternative Suggester: Find pin-compatible and functionally equivalent parts
- BOM Checker: Cross-check Bill of Materials for compatibility issues
- Design Rule Checker: Validate design constraints
- Pin Mux Solver: Resolve pin assignment conflicts
- Power Budget Calculator: Calculate system power consumption
"""

__version__ = "1.0.0"
from .hard_filter import HardFilter
from .ranking import RankingEngine
from .near_miss import NearMissEngine
from .alternative_suggester import AlternativeSuggester
from .design_rule_checker import DesignRuleChecker
from .pin_mux_solver import PinMuxSolver
from .power_budget_calculator import PowerBudgetCalculator
from .bom_checker import BOMCompatibilityChecker

__all__ = [
    "HardFilter",
    "RankingEngine",
    "NearMissEngine",
    "AlternativeSuggester",
    "DesignRuleChecker",
    "PinMuxSolver",
    "PowerBudgetCalculator",
    "BOMCompatibilityChecker",
]
