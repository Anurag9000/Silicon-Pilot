"""
End-to-End Example: Phase 2 Intent-to-Architecture Pipeline

Demonstrates the complete flow from user intent to BOM + configuration notes.
"""

from templates.template_system import TemplateLoader
from llm.intent_classifier import IntentPipeline
from architecture.compiler import ArchitectureBuilder, ConstraintCompiler
from solver.subsystems.multi_solver import (
    PowerSolver, TransceiverSolver, SensorSolver,
    PowerRequirements, TransceiverRequirements, SensorRequirements,
    PowerComponentType, TransceiverType, SensorType
)
from architecture.bom_composer import BOMComposer
from architecture.config_generator import ConfigurationGenerator


def example_motor_controller():
    """
    Example: CAN Motor Controller
    
    User input: "I want to build a CAN motor controller for BLDC motors"
    """
    print("=" * 60)
    print("Example 1: CAN Motor Controller")
    print("=" * 60)
    print()
    
    # Step 1: Load templates
    print("Step 1: Loading templates...")
    loader = TemplateLoader()
    print(f"✓ Loaded {len(loader.templates)} templates")
    print()
    
    # Step 2: Classify intent
    print("Step 2: Classifying user intent...")
    user_input = "I want to build a CAN motor controller for BLDC motors"
    print(f"User: \"{user_input}\"")
    
    pipeline = IntentPipeline(loader)
    intent, matches = pipeline.process(user_input, top_k=3)
    
    print(f"\n✓ Intent classified:")
    print(f"  Device type: {intent.device_type}")
    print(f"  Keywords: {', '.join(intent.keywords)}")
    print(f"  Confidence: {intent.confidence:.2f}")
    
    print(f"\n✓ Template matches:")
    for match in matches:
        print(f"  - {match.template_name} (score: {match.score:.1f})")
    print()
    
    # Step 3: Load best template
    print("Step 3: Loading template...")
    template = loader.get_template(matches[0].template_id)
    print(f"✓ Selected template: {template.name}")
    print()
    
    # Step 4: Answer questions (simulated)
    print("Step 4: Answering template questions...")
    answers = {
        'motor_type': 'BLDC',
        'supply_voltage': [12, 24],
        'peak_current': 15,
        'control_mode': 'Closed Loop (Encoder)',
        'can_fd_required': False,
        'isolation_required': False,
        'temperature_grade': 'Industrial (-40 to 85°C)',
        'pwm_frequency': 20,
    }
    
    for qid, answer in answers.items():
        print(f"  {qid}: {answer}")
    print()
    
    # Step 5: Build architecture
    print("Step 5: Building architecture graph...")
    builder = ArchitectureBuilder(template)
    builder.build_initial_graph()
    
    for qid, answer in answers.items():
        builder.add_answer(qid, answer)
    
    architecture = builder.apply_rules()
    print(f"✓ Architecture built with {len(architecture.subsystems)} subsystems:")
    for name in architecture.subsystems.keys():
        print(f"  - {name}")
    print()
    
    # Step 6: Compile to RequirementSpec
    print("Step 6: Compiling constraints...")
    compiler = ConstraintCompiler()
    spec = compiler.compile(architecture)
    print(f"✓ Compiled to RequirementSpec")
    print(f"  Flash: ≥{spec.flash_kb_min}KB")
    print(f"  RAM: ≥{spec.sram_kb_min}KB")
    print(f"  Peripherals: {spec.peripherals_min}")
    print()
    
    # Step 7: Solve subsystems
    print("Step 7: Solving subsystems...")
    
    # Power subsystem
    power_solver = PowerSolver()
    power_req = PowerRequirements(
        component_type=PowerComponentType.BUCK_CONVERTER,
        input_voltage_min=12,
        input_voltage_max=24,
        output_voltage=3.3,
        output_current_ma=500,
        efficiency_min=0.85
    )
    power_components = power_solver.solve(power_req)
    print(f"✓ Power: {len(power_components)} components found")
    if power_components:
        print(f"  Recommended: {power_components[0].mpn}")
    
    # Transceiver subsystem
    transceiver_solver = TransceiverSolver()
    transceiver_req = TransceiverRequirements(
        transceiver_type=TransceiverType.CAN,
        voltage_supply=3.3,
        min_bitrate=500000
    )
    transceivers = transceiver_solver.solve(transceiver_req)
    print(f"✓ Transceiver: {len(transceivers)} components found")
    if transceivers:
        print(f"  Recommended: {transceivers[0].mpn}")
    print()
    
    # Step 8: Compose BOM
    print("Step 8: Composing BOM...")
    composer = BOMComposer()
    
    # Simulated MCU recommendation
    class MockMCU:
        mpn = "STM32F405RGT6"
        manufacturer = "STMicroelectronics"
        family = "STM32F4"
    
    bom = composer.compose(
        device_name="CAN Motor Controller",
        device_type="motor_controller",
        mcu_recommendation=MockMCU(),
        power_recommendations=power_components[:1] if power_components else [],
        transceiver_recommendations=transceivers[:1] if transceivers else [],
    )
    
    print(f"✓ BOM composed:")
    print(f"  Total parts: {bom.total_parts}")
    if bom.total_estimated_cost_usd:
        print(f"  Estimated cost: ${bom.total_estimated_cost_usd:.2f}")
    print()
    
    # Step 9: Generate configuration notes
    print("Step 9: Generating configuration notes...")
    config_gen = ConfigurationGenerator()
    config = config_gen.generate(architecture, bom, answers)
    
    print(f"✓ Configuration notes generated:")
    if config.clock_config:
        print(f"  System clock: {config.clock_config.system_clock_mhz} MHz")
    print(f"  Pin assignments: {len(config.pin_assignments)}")
    print(f"  Power budget items: {len(config.power_budget)}")
    print()
    
    # Step 10: Export
    print("Step 10: Exporting outputs...")
    
    # Export BOM to Markdown
    bom_md = composer.export_to_markdown(bom)
    with open("output_bom_motor_controller.md", "w") as f:
        f.write(bom_md)
    print("✓ BOM exported to: output_bom_motor_controller.md")
    
    # Export config to Markdown
    config_md = config_gen.export_to_markdown(config)
    with open("output_config_motor_controller.md", "w") as f:
        f.write(config_md)
    print("✓ Config exported to: output_config_motor_controller.md")
    print()
    
    print("=" * 60)
    print("✅ Complete! Motor controller design ready.")
    print("=" * 60)


def example_sensor_node():
    """
    Example: IoT Sensor Node
    
    User input: "I want to build a battery-powered LoRa sensor node"
    """
    print("\n\n")
    print("=" * 60)
    print("Example 2: IoT Sensor Node")
    print("=" * 60)
    print()
    
    # Abbreviated example
    print("User: \"I want to build a battery-powered LoRa sensor node\"")
    print()
    
    loader = TemplateLoader()
    pipeline = IntentPipeline(loader)
    intent, matches = pipeline.process("battery-powered LoRa sensor node", top_k=1)
    
    print(f"✓ Matched template: {matches[0].template_name if matches else 'None'}")
    print(f"✓ Device type: {intent.device_type}")
    print()
    
    # Simulated answers
    answers = {
        'battery_type': 'Li-ion (3.7V)',
        'battery_life_target': '1 year',
        'sensor_types': ['Temperature', 'Humidity'],
        'wireless_protocol': 'LoRa',
        'lora_region': 'US915',
        'sampling_interval': 15,
    }
    
    print("Answers:")
    for qid, answer in answers.items():
        print(f"  {qid}: {answer}")
    print()
    
    # Build architecture
    template = loader.get_template(matches[0].template_id) if matches else None
    if template:
        builder = ArchitectureBuilder(template)
        builder.build_initial_graph()
        
        for qid, answer in answers.items():
            builder.add_answer(qid, answer)
        
        architecture = builder.apply_rules()
        
        print(f"✓ Architecture: {len(architecture.subsystems)} subsystems")
        
        # Solve sensors
        sensor_solver = SensorSolver()
        temp_sensor_req = SensorRequirements(
            sensor_type=SensorType.TEMPERATURE,
            interface="i2c",
            voltage_supply=3.3,
            max_current_ua=100
        )
        sensors = sensor_solver.solve(temp_sensor_req)
        
        print(f"✓ Sensor: {sensors[0].mpn if sensors else 'None'}")
        print()
    
    print("=" * 60)
    print("✅ Complete! Sensor node design ready.")
    print("=" * 60)


if __name__ == "__main__":
    # Run examples
    example_motor_controller()
    example_sensor_node()
    
    print("\n\n🎉 Phase 2 Pipeline Demonstration Complete!")
    print("\nNext steps:")
    print("1. Expand template library (10+ templates)")
    print("2. Integrate with real MCU database")
    print("3. Add more subsystem solvers")
    print("4. Build web UI for user interaction")
