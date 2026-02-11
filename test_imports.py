from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("Importing core.models...")
from core.models import RequirementSpec
print(f"RequirementSpec: {RequirementSpec}")

print("Importing templates.template_system...")
try:
    import templates.template_system
    print("Success importing templates.template_system")
except Exception:
    import traceback
    with open("trace.txt", "w") as f:
        traceback.print_exc(file=f)
    print("Failed importing templates.template_system. Traceback saved to trace.txt")
    

print("Importing architecture.compiler...")
from architecture.compiler import ConstraintCompiler
print("Success!")
