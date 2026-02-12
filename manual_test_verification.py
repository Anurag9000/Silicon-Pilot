
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

def test_ranking():
    print("Testing ranking.py...")
    try:
        from solver.ranking import RankingEngine
        engine = RankingEngine()
        # Test _calculate_power_score
        # Check if math is imported correctly
        score = engine._calculate_power_score({'standby_ua': 100})
        print(f"RankingEngine Power Score (100uA): {score}")
        assert 0.0 <= score <= 1.0
        print("PASS: ranking.py works.")
    except Exception as e:
        print(f"FAIL: ranking.py errored with {e}")
        import traceback
        traceback.print_exc()

def test_drc_import():
    print("Testing design_rule_checker.py import...")
    try:
        import solver.design_rule_checker
        print("PASS: design_rule_checker.py imports successfully.")
    except Exception as e:
        print(f"FAIL: design_rule_checker.py import failed with {e}")
        import traceback
        traceback.print_exc()

def test_alternative_suggester_import():
    print("Testing alternative_suggester.py import...")
    try:
        import solver.alternative_suggester
        print("PASS: alternative_suggester.py imports successfully.")
    except Exception as e:
        print(f"FAIL: alternative_suggester.py import failed with {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ranking()
    test_drc_import()
    test_alternative_suggester_import()
