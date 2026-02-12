
import sys
import os
from pathlib import Path

# Add root to python path
sys.path.insert(0, os.getcwd())

print("Importing core.models...")
from core.models import RequirementSpec

print("Importing templates.template_system...")
from templates.template_system import DeviceTemplate

print("Importing architecture.compiler...")
from architecture.compiler import ArchitectureBuilder, build_architecture_from_template

print("Importing solver.pin_mux_solver...")
from solver.pin_mux_solver import PinMuxSolver

print("Importing solver.power_budget_calculator...")
from solver.power_budget_calculator import PowerBudgetCalculator


print("Imports successful!")

# Try to use ArchitectureBuilder
print("Testing ArchitectureBuilder...")
from templates.template_system import DeviceTemplate, SubsystemTemplate
from core.ontology import DeviceType

tmpl = DeviceTemplate(
    id="test", name="Test", device_type=DeviceType.WEARABLE, description="Test",
    subsystems={"compute": SubsystemTemplate()},
    questions=[], rules=[], tags=[], use_cases=[]
)

try:
    arch = build_architecture_from_template(tmpl, {})
    print("Build successful!")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Build failed: {e}")

# Try PinMuxSolver (mock pool)
print("Testing PinMuxSolver...")
class MockPool:
    pass
try:
    s = PinMuxSolver(MockPool())
    print("Solver init successful!")
except Exception as e:
    print(f"Solver init failed: {e}")

print("Testing LLMOrchestrator...")
try:
    from llm.orchestrator import LLMOrchestrator
    llm = LLMOrchestrator()
    print("LLM init successful!")
except Exception as e:
    print(f"LLM init failed: {e}")

print("Testing QuestionEngine...")
try:
    from questions.engine import QuestionEngine
    qe = QuestionEngine()
    print("QuestionEngine init successful!")
except Exception as e:
    print(f"QuestionEngine init failed: {e}")

