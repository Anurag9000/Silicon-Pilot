"""
Stress Test Script for HardwareGenius

Loads golden scenarios and runs them against the Ranking Engine.
Simulates high load if needed.
"""
import json
import time
import os
import sys

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solver.ml_ranking import RankingEngine

def load_scenarios():
    with open("tests/golden_scenarios.json", "r") as f:
        return json.load(f)

def mock_candidates():
    # Mock some data for stress testing the RANKER logic
    # In real integration, this would query the DB
    return [
        {
            "id": "1", "mpn": "STM32F030F4P6", "manufacturer": "ST", 
            "cost_usd": 0.85, "stock": 15000, 
            "specs": {"flash_kb": 16, "sram_kb": 4, "core": "Cortex-M0"}
        },
        {
            "id": "2", "mpn": "STM32F405RGT6", "manufacturer": "ST", 
            "cost_usd": 6.50, "stock": 2000, 
            "specs": {"flash_kb": 1024, "sram_kb": 192, "core": "Cortex-M4"}
        },
        {
            "id": "3", "mpn": "STM32L476RGT6", "manufacturer": "ST", 
            "cost_usd": 4.20, "stock": 5000, 
            "specs": {"flash_kb": 1024, "sram_kb": 128, "core": "Cortex-M4"}
        },
        {
            "id": "4", "mpn": "STM32H743ZIT6", "manufacturer": "ST", 
            "cost_usd": 12.00, "stock": 500, 
            "specs": {"flash_kb": 2048, "sram_kb": 1024, "core": "Cortex-M7"}
        }
    ]

def run_stress_test(iterations=100):
    print(f"Starting Stress Test ({iterations} iterations)...")
    scenarios = load_scenarios()
    candidates = mock_candidates()
    engine = RankingEngine()
    
    start_time = time.time()
    
    for i in range(iterations):
        for scenario in scenarios:
            # Run ranking
            ranked = engine.rank_candidates(candidates, scenario['requirements'])
            # Validation logic could go here
            pass
            
    end_time = time.time()
    duration = end_time - start_time
    avg_latency = (duration / (iterations * len(scenarios))) * 1000
    
    print(f"Completed {iterations * len(scenarios)} ranking operations.")
    print(f"Total Time: {duration:.4f}s")
    print(f"Avg Latency per Request: {avg_latency:.4f}ms")
    
    if avg_latency < 5.0:
        print("[PASS] Latency < 5ms")
    else:
        print("[WARN] Latency > 5ms")

if __name__ == "__main__":
    run_stress_test()
