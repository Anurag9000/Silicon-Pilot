"""
Complete End-to-End Demonstration

Shows the full pipeline from user intent to exported CAD files:
1. Intent classification
2. Template matching
3. Architecture building
4. Multi-subsystem solving
5. BOM composition
6. Configuration generation
7. Enhanced exports (Eagle, KiCad, STM32CubeMX, PDF)
"""

import asyncio
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from templates.template_system import TemplateLoader
from llm.intent_classifier import IntentParser, TemplateMatcher
from architecture.compiler import ArchitectureBuilder, ConstraintCompiler
from architecture.bom_composer import BOMComposer
from architecture.config_generator import ConfigurationGenerator
from architecture.enhanced_exports import ExportManager


async def run_complete_demo():
    """Run complete end-to-end demonstration"""
    
    print("=" * 80)
    print("Silicon-Pilot - Complete End-to-End Demonstration")
    print("=" * 80)
    print()
    
    # ========================================================================
    # Step 1: User Intent
    # ========================================================================
    
    user_input = "I want to build a CAN motor controller for BLDC motors at 24V"
    print(f"📝 User Input:")
    print(f"   \"{user_input}\"")
    print()
    
    # ========================================================================
    # Step 2: Intent Classification
    # ========================================================================
    
    print("🔍 Step 1: Intent Classification")
    parser = IntentParser(use_llm=False)  # Use keyword fallback
    intent = parser.parse_intent(user_input)
    
    print(f"   Device Type: {intent.device_type}")
    print(f"   Keywords: {', '.join(intent.keywords)}")
    print(f"   Extracted Params: {intent.extracted_params}")
    print()
    
    # ========================================================================
    # Step 3: Template Matching
    # ========================================================================
    
    print("🎯 Step 2: Template Matching")
    template_dir = Path(__file__).parent.parent / "templates"
    loader = TemplateLoader(str(template_dir))
    matcher = TemplateMatcher(loader)
    
    matches = matcher.match_templates(intent)
    
    if not matches:
        print("   ❌ No matching templates found")
        return
    
    best_match = matches[0]
    print(f"   Best Match: {best_match.template_id}")
    print(f"   Confidence: {best_match.confidence:.2%}")
    print(f"   Reason: {best_match.match_reason}")
    print()
    
    # ========================================================================
    # Step 4: Load Template
    # ========================================================================
    
    print("📋 Step 3: Loading Template")
    template = loader.load_template(best_match.template_id)
    print(f"   Template: {template.name}")
    print(f"   Device Type: {template.device_type}")
    print(f"   Subsystems: {len(template.subsystems)}")
    print(f"   Questions: {len(template.questions)}")
    print()
    
    # ========================================================================
    # Step 5: Simulate User Answers
    # ========================================================================
    
    print("💬 Step 4: User Answers (Simulated)")
    answers = {
        "motor_type": "BLDC",
        "supply_voltage": "24",
        "peak_current": "10",
        "control_mode": "Closed-loop (with encoder)",
        "can_bitrate": "500 kbps",
        "environment": "Industrial (-40 to 85°C)",
        "safety_features": "Basic (E-stop)",
        "firmware_preference": "Vendor HAL"
    }
    
    for q_id, answer in answers.items():
        question = next((q for q in template.questions if q.id == q_id), None)
        if question:
            print(f"   Q: {question.text}")
            print(f"   A: {answer}")
    print()
    
    # ========================================================================
    # Step 6: Build Architecture
    # ========================================================================
    
    print("🏗️  Step 5: Building Architecture")
    builder = ArchitectureBuilder()
    architecture = builder.build_architecture(template, answers)
    
    print(f"   Subsystems: {len(architecture.subsystems)}")
    for name, subsystem in architecture.subsystems.items():
        print(f"     - {name}: {len(subsystem.functions)} functions")
    print()
    
    # ========================================================================
    # Step 7: Compile Constraints
    # ========================================================================
    
    print("⚙️  Step 6: Compiling Constraints")
    compiler = ConstraintCompiler()
    req_spec = compiler.compile_constraints(architecture)
    
    print(f"   MCU Requirements:")
    print(f"     - Core: {req_spec.get('core_arch', 'N/A')}")
    print(f"     - Flash: ≥{req_spec.get('min_flash_kb', 0)} KB")
    print(f"     - RAM: ≥{req_spec.get('min_sram_kb', 0)} KB")
    print(f"     - CAN: ≥{req_spec.get('can_count', 0)}")
    print()
    
    # ========================================================================
    # Step 8: Multi-Subsystem Solving
    # ========================================================================
    
    print("🔧 Step 7: Multi-Subsystem Solving")
    
    # Simulate component recommendations (would use real solvers)
    components = [
        {
            "subsystem": "compute",
            "category": "MCU",
            "manufacturer": "STMicroelectronics",
            "mpn": "STM32F405RGT6",
            "description": "ARM Cortex-M4, 168MHz, 1MB Flash, 192KB RAM",
            "package": "LQFP-64",
            "quantity": 1,
            "price_usd": 5.50,
            "datasheet_url": "https://www.st.com/resource/en/datasheet/stm32f405rg.pdf",
            "alternatives": ["STM32F407VGT6", "STM32F446RET6"]
        },
        {
            "subsystem": "power",
            "category": "Buck Converter",
            "manufacturer": "Texas Instruments",
            "mpn": "TPS62160",
            "description": "3-17V input, 3.3V/1A output, 95% efficiency",
            "package": "SOT-23-6",
            "quantity": 1,
            "price_usd": 1.20,
            "datasheet_url": "https://www.ti.com/lit/ds/symlink/tps62160.pdf",
            "alternatives": ["TPS62162", "LM3671"]
        },
        {
            "subsystem": "communication",
            "category": "CAN Transceiver",
            "manufacturer": "Texas Instruments",
            "mpn": "SN65HVD230",
            "description": "3.3V CAN transceiver, 1Mbps",
            "package": "SOIC-8",
            "quantity": 1,
            "price_usd": 0.60,
            "datasheet_url": "https://www.ti.com/lit/ds/symlink/sn65hvd230.pdf",
            "alternatives": ["TJA1050", "MCP2551"]
        },
        {
            "subsystem": "protection",
            "category": "TVS Diode",
            "manufacturer": "Littelfuse",
            "mpn": "SMBJ24A",
            "description": "24V TVS diode for CAN protection",
            "package": "SMB",
            "quantity": 2,
            "price_usd": 0.18,
            "datasheet_url": "https://www.littelfuse.com/~/media/electronics/datasheets/tvs_diodes/littelfuse_tvs_diode_smbj_datasheet.pdf",
            "alternatives": ["SMAJ24A"]
        }
    ]
    
    for comp in components:
        print(f"   {comp['category']}: {comp['manufacturer']} {comp['mpn']}")
        print(f"     ${comp['price_usd']:.2f} | {comp['package']}")
    
    total_cost = sum(c['price_usd'] * c['quantity'] for c in components)
    print(f"\n   Total BOM Cost: ${total_cost:.2f}")
    print()
    
    # ========================================================================
    # Step 9: Generate Configuration Notes
    # ========================================================================
    
    print("📝 Step 8: Generating Configuration Notes")
    
    config = {
        "clock": {
            "hse_mhz": 8,
            "pll_m": 8,
            "pll_n": 336,
            "pll_p": 2,
            "sysclk_mhz": 168,
            "ahb_mhz": 168,
            "apb1_mhz": 42,
            "apb2_mhz": 84
        },
        "pins": {
            "PA8": {"mode": "TIM1_CH1", "signal": "PWM", "description": "Motor Phase A"},
            "PA9": {"mode": "TIM1_CH2", "signal": "PWM", "description": "Motor Phase B"},
            "PA10": {"mode": "TIM1_CH3", "signal": "PWM", "description": "Motor Phase C"},
            "PA0": {"mode": "ADC1_IN0", "signal": "ADC", "description": "Current Sense A"},
            "PA1": {"mode": "ADC1_IN1", "signal": "ADC", "description": "Current Sense B"},
            "PA2": {"mode": "ADC1_IN2", "signal": "ADC", "description": "Current Sense C"},
            "PB8": {"mode": "CAN1_RX", "signal": "CAN", "description": "CAN RX"},
            "PB9": {"mode": "CAN1_TX", "signal": "CAN", "description": "CAN TX"}
        },
        "power_budget": {
            "mcu_active_ma": 52,
            "can_transceiver_ma": 70,
            "total_ma": 150,
            "voltage": 3.3
        },
        "firmware": {
            "hal": "STM32CubeF4",
            "rtos": "FreeRTOS (recommended)",
            "middleware": "CAN stack",
            "motor_control": "FOC library"
        }
    }
    
    print(f"   Clock: {config['clock']['sysclk_mhz']} MHz system clock")
    print(f"   Pins: {len(config['pins'])} configured")
    print(f"   Power Budget: {config['power_budget']['total_ma']} mA @ {config['power_budget']['voltage']}V")
    print()
    
    # ========================================================================
    # Step 10: Enhanced Exports
    # ========================================================================
    
    print("📤 Step 9: Exporting to CAD Tools")
    
    export_manager = ExportManager()
    project_name = "BLDC_MotorController_v1"
    output_dir = Path(__file__).parent.parent / "exports"
    output_dir.mkdir(exist_ok=True)
    
    export_manager.export_all(components, config, project_name, str(output_dir))
    
    print()
    
    # ========================================================================
    # Summary
    # ========================================================================
    
    print("=" * 80)
    print("✅ Complete Pipeline Executed Successfully!")
    print("=" * 80)
    print()
    print("📊 Summary:")
    print(f"   Template: {template.name}")
    print(f"   Components: {len(components)}")
    print(f"   Total Cost: ${total_cost:.2f}")
    print(f"   Exports: {len(['eagle', 'kicad', 'altium', 'cubemx', 'pdf'])} formats")
    print()
    print("📁 Output Files:")
    print(f"   {output_dir}/{project_name}_eagle.xml")
    print(f"   {output_dir}/{project_name}_kicad.csv")
    print(f"   {output_dir}/{project_name}_altium.csv")
    print(f"   {output_dir}/{project_name}.ioc (STM32CubeMX)")
    print(f"   {output_dir}/{project_name}_report.pdf")
    print()
    print("🚀 Ready for PCB design and firmware development!")
    print()


if __name__ == "__main__":
    asyncio.run(run_complete_demo())
