
import sys
import traceback

print("1. Importing core.models...")
try:
    import core.models
    print("   Success.")
except:
    traceback.print_exc()

print("\n2. Importing RequirementSpec from core.models...")
try:
    from core.models import RequirementSpec
    print("   Success.")
except:
    traceback.print_exc()

print("\n3. Importing solver.ranking...")
try:
    import solver.ranking
    print("   Success.")
except:
    traceback.print_exc()

print("\n4. Importing RankingEngine from solver.ranking...")
try:
    from solver.ranking import RankingEngine
    print("   Success.")
except:
    traceback.print_exc()
