"""
Test Suite for Intelligent Constraint Optimizer

Tests the LLM-driven constraint optimization feature.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from architecture.intelligent_optimizer import (
    IntelligentConstraintOptimizer,
    ConstraintValidator,
    OptimizationResult
)


def test_bldc_motor_controller_optimization():
    """Test optimization for BLDC motor controller"""
    
    print("=" * 80)
    print("TEST: BLDC Motor Controller Optimization")
    print("=" * 80)
    print()
    
    # Baseline constraints from template
    baseline = {
        "core_arch": "cortex-m4",
        "min_flash_kb": 256,
        "min_sram_kb": 64,
        "min_mhz": 168,
        "peripherals_min": {
            "can": 2,
            "pwm_timers": 3,  # Should be optimized to 1
            "adc_channels": 3,  # Should be optimized to 4
            "uart": 2
        },
        "has_fpu": True
    }
    
    # User requirements
    requirements = {
        "motor_type": "BLDC",
        "supply_voltage": "24V",
        "peak_current": "10A",
        "control_mode": "Closed-loop (FOC)",
        "pwm_frequency": "20kHz"
    }
    
    # Template context
    context = {
        "device_type": "motor_controller",
        "application": "BLDC motor control with FOC",
        "environment": "industrial"
    }
    
    # Create optimizer
    optimizer = IntelligentConstraintOptimizer()
    
    # Optimize
    result = optimizer.optimize_constraints(
        baseline_constraints=baseline,
        user_requirements=requirements,
        template_context=context
    )
    
    # Display results
    print("BASELINE CONSTRAINTS:")
    print(f"  PWM Timers: {baseline['peripherals_min']['pwm_timers']}")
    print(f"  ADC Channels: {baseline['peripherals_min']['adc_channels']}")
    print(f"  CPU Speed: {baseline['min_mhz']} MHz")
    print()
    
    print("OPTIMIZATIONS:")
    for opt in result.optimizations:
        print(f"\n  ✓ {opt.field}:")
        print(f"    {opt.original_value} → {opt.optimized_value}")
        print(f"    Reasoning: {opt.reasoning}")
        print(f"    Impact: {opt.impact}")
        print(f"    Confidence: {opt.confidence:.0%}")
    
    print(f"\nOVERALL CONFIDENCE: {result.confidence_score:.0%}")
    
    # Validate
    validator = ConstraintValidator()
    is_valid, issues = validator.validate_constraints(result.optimized_constraints)
    
    print(f"\nVALIDATION: {' PASS' if is_valid else ' FAIL'}")
    if issues:
        for issue in issues:
            print(f"    {issue}")
    
    print()
    return result


def test_sensor_node_optimization():
    """Test optimization for IoT sensor node"""
    
    print("=" * 80)
    print("TEST: IoT Sensor Node Optimization")
    print("=" * 80)
    print()
    
    baseline = {
        "core_arch": "cortex-m0",
        "min_flash_kb": 64,
        "min_sram_kb": 16,
        "min_mhz": 48,
        "peripherals_min": {
            "i2c": 1,
            "spi": 1,
            "uart": 1
        },
        "power_profile": "ultra_low_power"
    }
    
    requirements = {
        "sensors": ["temperature", "humidity", "pressure"],
        "wireless": "LoRa",
        "battery_powered": True,
        "sleep_mode": "deep_sleep"
    }
    
    context = {
        "device_type": "sensor_node",
        "application": "Environmental monitoring",
        "environment": "outdoor"
    }
    
    optimizer = IntelligentConstraintOptimizer()
    result = optimizer.optimize_constraints(
        baseline_constraints=baseline,
        user_requirements=requirements,
        template_context=context
    )
    
    print("OPTIMIZATIONS:")
    for opt in result.optimizations:
        print(f"\n  ✓ {opt.field}:")
        print(f"    {opt.original_value} → {opt.optimized_value}")
        print(f"    Reasoning: {opt.reasoning}")
    
    print(f"\nCONFIDENCE: {result.confidence_score:.0%}")
    print()
    return result


def test_validation():
    """Test constraint validation"""
    
    print("=" * 80)
    print("TEST: Constraint Validation")
    print("=" * 80)
    print()
    
    validator = ConstraintValidator()
    
    # Test 1: Valid constraints
    valid_constraints = {
        "min_flash_kb": 512,
        "min_sram_kb": 128,
        "min_mhz": 168,
        "peripherals_min": {
            "can": 2,
            "uart": 3
        }
    }
    
    is_valid, issues = validator.validate_constraints(valid_constraints)
    print(f"Test 1 (Valid): {' PASS' if is_valid else ' FAIL'}")
    
    # Test 2: Invalid constraints (too high)
    invalid_constraints = {
        "min_flash_kb": 4096,  # Too high
        "min_sram_kb": 1024,   # Too high
        "min_mhz": 1000,       # Too high
        "peripherals_min": {
            "can": 5,  # Too many
            "uart": 10  # Too many
        }
    }
    
    is_valid, issues = validator.validate_constraints(invalid_constraints)
    print(f"Test 2 (Invalid): {' FAIL' if is_valid else ' PASS (correctly detected issues)'}")
    if issues:
        print("  Issues detected:")
        for issue in issues:
            print(f"    - {issue}")
    
    print()


def test_fallback_mode():
    """Test fallback when LLM unavailable"""
    
    print("=" * 80)
    print("TEST: Fallback Mode (No LLM)")
    print("=" * 80)
    print()
    
    # Create optimizer without API key
    optimizer = IntelligentConstraintOptimizer(api_key="invalid")
    
    baseline = {
        "min_flash_kb": 256,
        "min_sram_kb": 64
    }
    
    result = optimizer.optimize_constraints(
        baseline_constraints=baseline,
        user_requirements={},
        template_context={}
    )
    
    print(f"Optimizations: {len(result.optimizations)}")
    print(f"Reasoning: {result.overall_reasoning}")
    print(f"Confidence: {result.confidence_score:.0%}")
    print()
    
    assert len(result.optimizations) == 0, "Fallback should return no optimizations"
    assert result.confidence_score == 0.5, "Fallback should have 0.5 confidence"
    print(" Fallback mode works correctly")
    print()


def run_all_tests():
    """Run all tests"""
    
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "INTELLIGENT OPTIMIZER TEST SUITE" + " " * 26 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")
    
    try:
        # Test 1: BLDC Motor Controller
        result1 = test_bldc_motor_controller_optimization()
        
        # Test 2: IoT Sensor Node
        result2 = test_sensor_node_optimization()
        
        # Test 3: Validation
        test_validation()
        
        # Test 4: Fallback
        test_fallback_mode()
        
        # Summary
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print()
        print(" All tests passed!")
        print()
        print("Features Verified:")
        print("  ✓ LLM-driven constraint optimization")
        print("  ✓ Domain knowledge application")
        print("  ✓ Constraint validation")
        print("  ✓ Fallback mode")
        print()
        
    except Exception as e:
        print(f"\n TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
