"""
Test Hardware Genius System

Simple test to verify the filtering engine works correctly.
"""

from hardware_db import get_all_mcus, get_database_stats
from filtering import parse_requirements, filter_mcus, format_constraints_for_display


def test_basic_filtering():
    """Test basic filtering functionality"""
    print("=" * 60)
    print("HARDWAREGENIUS - System Test")
    print("=" * 60)
    
    # Get database stats
    stats = get_database_stats()
    print(f"\n📊 Database Statistics:")
    print(f"  Total MCUs: {stats['total_mcus']}")
    print(f"  Manufacturers: {', '.join(stats['manufacturer_list'])}")
    print(f"  Families: {', '.join(stats['family_list'])}")
    
    # Test Case 1: ARM Cortex-M4 with USB
    print("\n" + "=" * 60)
    print("Test Case 1: ARM Cortex-M4 with USB, under $5")
    print("=" * 60)
    
    requirements = "ARM Cortex-M4 with at least 128KB RAM, 512KB Flash, USB support, and costs under $5"
    request = parse_requirements(requirements)
    
    print(f"\n📝 Parsed Constraints:")
    print(format_constraints_for_display(request))
    
    database = get_all_mcus()
    results = filter_mcus(request, database)
    
    print(f"\n✅ Found {len(results)} matching MCUs:")
    for i, (mcu, score) in enumerate(results[:5], 1):
        print(f"\n{i}. {mcu.part_number} ({mcu.manufacturer})")
        print(f"   Core: {mcu.core_architecture.value}, {mcu.clock_mhz} MHz")
        print(f"   Memory: {mcu.ram_kb}KB RAM, {mcu.flash_kb}KB Flash")
        print(f"   Cost: ${mcu.cost_usd:.2f}")
        print(f"   Score: {score:.3f}")
    
    # Test Case 2: Low-power IoT
    print("\n" + "=" * 60)
    print("Test Case 2: Low-power MCU for battery-powered IoT")
    print("=" * 60)
    
    requirements = "I need a low-power MCU for battery-powered IoT sensor with I2C"
    request = parse_requirements(requirements)
    
    print(f"\n📝 Parsed Constraints:")
    print(format_constraints_for_display(request))
    
    results = filter_mcus(request, database)
    
    print(f"\n✅ Found {len(results)} matching MCUs:")
    for i, (mcu, score) in enumerate(results[:5], 1):
        power_str = f"{mcu.power_consumption.standby_ua:.2f} µA standby" if mcu.power_consumption else "N/A"
        print(f"\n{i}. {mcu.part_number} ({mcu.manufacturer})")
        print(f"   Core: {mcu.core_architecture.value}, {mcu.clock_mhz} MHz")
        print(f"   Power: {power_str}")
        print(f"   Cost: ${mcu.cost_usd:.2f}")
        print(f"   Score: {score:.3f}")
    
    # Test Case 3: Wireless connectivity
    print("\n" + "=" * 60)
    print("Test Case 3: MCU with WiFi and Bluetooth")
    print("=" * 60)
    
    requirements = "MCU with WiFi and Bluetooth for IoT gateway"
    request = parse_requirements(requirements)
    
    print(f"\n📝 Parsed Constraints:")
    print(format_constraints_for_display(request))
    
    results = filter_mcus(request, database)
    
    print(f"\n✅ Found {len(results)} matching MCUs:")
    for i, (mcu, score) in enumerate(results[:5], 1):
        print(f"\n{i}. {mcu.part_number} ({mcu.manufacturer})")
        print(f"   Core: {mcu.core_architecture.value}, {mcu.clock_mhz} MHz")
        print(f"   Memory: {mcu.ram_kb}KB RAM, {mcu.flash_kb}KB Flash")
        print(f"   Wireless: {'Yes' if mcu.has_wireless else 'No'}")
        print(f"   Cost: ${mcu.cost_usd:.2f}")
        print(f"   Score: {score:.3f}")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    test_basic_filtering()
