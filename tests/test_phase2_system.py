"""
Test Suite for Phase 2: Intent-to-Architecture System

Tests:
- Template loading and validation
- Intent classification
- Template matching
- Architecture compilation
- BOM generation
- End-to-end pipeline
"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from templates.template_system import TemplateLoader, TemplateValidator
from llm.intent_classifier import IntentParser, TemplateMatcher
from architecture.compiler import ArchitectureBuilder, ConstraintCompiler
from architecture.bom_composer import BOMComposer
from solver.subsystems.additional_solvers import (
    MemorySolver, DisplaySolver, ConnectorSolver, ProtectionSolver,
    MemoryRequirement, DisplayRequirement, ConnectorRequirement, ProtectionRequirement
)


# ============================================================================
# Template System Tests
# ============================================================================

class TestTemplateSystem:
    """Test template loading and validation"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.template_dir = Path(__file__).parent.parent / "templates"
        self.loader = TemplateLoader(str(self.template_dir))
        self.validator = TemplateValidator()
    
    def test_template_loading(self):
        """Test that all templates load successfully"""
        templates = self.loader.load_all_templates()
        assert len(templates) >= 10, f"Expected at least 10 templates, found {len(templates)}"
        
        # Check specific templates exist
        template_ids = [t.id for t in templates]
        expected_ids = [
            "can_motor_controller_v1",
            "iot_sensor_node_v1",
            "environmental_data_logger_v1",
            "iot_gateway_v1",
            "wearable_device_v1",
            "industrial_io_module_v1",
            "robotics_controller_v1",
            "audio_device_v1",
            "smart_appliance_v1",
            "display_controller_v1"
        ]
        for expected_id in expected_ids:
            assert expected_id in template_ids, f"Template {expected_id} not found"
    
    def test_template_validation(self):
        """Test that all templates pass validation"""
        templates = self.loader.load_all_templates()
        errors = self.validator.validate_all_templates(self.loader)
        
        assert len(errors) == 0, f"Template validation errors: {errors}"
    
    def test_motor_controller_template(self):
        """Test motor controller template structure"""
        template = self.loader.load_template("can_motor_controller_v1")
        
        assert template is not None
        assert template.device_type == "motor_controller"
        assert "compute" in template.subsystems
        assert "power" in template.subsystems
        assert len(template.questions) >= 5
        assert len(template.rules) >= 3


# ============================================================================
# Intent Classification Tests
# ============================================================================

class TestIntentClassification:
    """Test intent parsing and template matching"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.template_dir = Path(__file__).parent.parent / "templates"
        self.loader = TemplateLoader(str(self.template_dir))
        self.parser = IntentParser(use_llm=False)  # Use keyword fallback
        self.matcher = TemplateMatcher(self.loader)
    
    def test_motor_controller_intent(self):
        """Test motor controller intent classification"""
        user_input = "I want to build a CAN motor controller for BLDC motors"
        
        intent = self.parser.parse_intent(user_input)
        
        assert intent.device_type in ["motor_controller", "robotics_controller"]
        assert "can" in [k.lower() for k in intent.keywords]
        assert "motor" in [k.lower() for k in intent.keywords]
    
    def test_sensor_node_intent(self):
        """Test sensor node intent classification"""
        user_input = "I need a battery-powered LoRa sensor node"
        
        intent = self.parser.parse_intent(user_input)
        
        assert intent.device_type == "sensor_node"
        assert "lora" in [k.lower() for k in intent.keywords]
    
    def test_template_matching(self):
        """Test template matching algorithm"""
        user_input = "I want to build a CAN motor controller"
        intent = self.parser.parse_intent(user_input)
        
        matches = self.matcher.match_templates(intent)
        
        assert len(matches) > 0
        assert matches[0].template_id == "can_motor_controller_v1"
        assert matches[0].confidence > 0.5


# ============================================================================
# Architecture Compilation Tests
# ============================================================================

class TestArchitectureCompilation:
    """Test architecture graph building and constraint compilation"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.template_dir = Path(__file__).parent.parent / "templates"
        self.loader = TemplateLoader(str(self.template_dir))
        self.builder = ArchitectureBuilder()
        self.compiler = ConstraintCompiler()
    
    def test_architecture_building(self):
        """Test architecture graph construction"""
        template = self.loader.load_template("can_motor_controller_v1")
        
        # Simulate user answers
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
        
        architecture = self.builder.build_architecture(template, answers)
        
        assert architecture is not None
        assert len(architecture.subsystems) >= 3
        assert "compute" in architecture.subsystems
        assert "power" in architecture.subsystems
    
    def test_constraint_compilation(self):
        """Test constraint compilation to RequirementSpec"""
        template = self.loader.load_template("can_motor_controller_v1")
        
        answers = {
            "motor_type": "BLDC",
            "supply_voltage": "24",
            "peak_current": "10"
        }
        
        architecture = self.builder.build_architecture(template, answers)
        req_spec = self.compiler.compile_constraints(architecture)
        
        assert req_spec is not None
        # Check that constraints were compiled
        # (exact structure depends on RequirementSpec model)


# ============================================================================
# Subsystem Solver Tests
# ============================================================================

class TestSubsystemSolvers:
    """Test additional subsystem solvers"""
    
    def test_memory_solver(self):
        """Test memory component solver"""
        solver = MemorySolver()
        
        req = MemoryRequirement(
            memory_type="flash",
            capacity_kb_min=4096,
            interface="spi"
        )
        
        results = solver.solve(req)
        
        assert len(results) > 0
        assert all(r.memory_type == "flash" for r in results)
        assert all(r.capacity_kb >= 4096 for r in results)
        assert all(r.interface == "spi" for r in results)
    
    def test_display_solver(self):
        """Test display component solver"""
        solver = DisplaySolver()
        
        req = DisplayRequirement(
            display_type="lcd",
            resolution="320x240",
            interface="spi",
            color=True
        )
        
        results = solver.solve(req)
        
        assert len(results) > 0
        assert all(r.display_type == "lcd" for r in results)
        assert all(r.resolution == "320x240" for r in results)
    
    def test_connector_solver(self):
        """Test connector component solver"""
        solver = ConnectorSolver()
        
        req = ConnectorRequirement(
            connector_type="usb",
            variant="usb_c"
        )
        
        results = solver.solve(req)
        
        assert len(results) > 0
        assert all(r.connector_type == "usb" for r in results)
    
    def test_protection_solver(self):
        """Test protection component solver"""
        solver = ProtectionSolver()
        
        req = ProtectionRequirement(
            protection_type="tvs",
            voltage_max=5.0
        )
        
        results = solver.solve(req)
        
        assert len(results) > 0
        assert all(r.protection_type == "tvs" for r in results)
        assert all(r.voltage_max >= 5.0 for r in results)


# ============================================================================
# End-to-End Pipeline Tests
# ============================================================================

class TestEndToEndPipeline:
    """Test complete pipeline from intent to BOM"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.template_dir = Path(__file__).parent.parent / "templates"
        self.loader = TemplateLoader(str(self.template_dir))
        self.parser = IntentParser(use_llm=False)
        self.matcher = TemplateMatcher(self.loader)
        self.builder = ArchitectureBuilder()
        self.compiler = ConstraintCompiler()
    
    def test_motor_controller_pipeline(self):
        """Test complete motor controller pipeline"""
        # Step 1: Parse intent
        user_input = "I want to build a CAN motor controller for BLDC motors"
        intent = self.parser.parse_intent(user_input)
        
        # Step 2: Match template
        matches = self.matcher.match_templates(intent)
        assert len(matches) > 0
        
        # Step 3: Load template
        template = self.loader.load_template(matches[0].template_id)
        assert template is not None
        
        # Step 4: Simulate answers
        answers = {
            "motor_type": "BLDC",
            "supply_voltage": "24",
            "peak_current": "10"
        }
        
        # Step 5: Build architecture
        architecture = self.builder.build_architecture(template, answers)
        assert architecture is not None
        
        # Step 6: Compile constraints
        req_spec = self.compiler.compile_constraints(architecture)
        assert req_spec is not None
        
        # Pipeline complete!
    
    def test_sensor_node_pipeline(self):
        """Test complete sensor node pipeline"""
        user_input = "I need a battery-powered LoRa sensor node"
        intent = self.parser.parse_intent(user_input)
        
        matches = self.matcher.match_templates(intent)
        assert len(matches) > 0
        
        template = self.loader.load_template(matches[0].template_id)
        assert template is not None


# ============================================================================
# Golden Scenario Tests
# ============================================================================

class TestGoldenScenarios:
    """Test golden scenarios with expected outputs"""
    
    def test_scenario_1_motor_controller(self):
        """Golden scenario: CAN motor controller"""
        # Expected: Template match, 8 questions, BOM with MCU + CAN transceiver
        pass  # TODO: Implement golden scenarios
    
    def test_scenario_2_iot_gateway(self):
        """Golden scenario: IoT gateway"""
        # Expected: Template match, multi-protocol support
        pass  # TODO: Implement golden scenarios


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
