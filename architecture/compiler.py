from __future__ import annotations
import logging
from pydantic import BaseModel, Field
from copy import deepcopy

from typing import Optional, Any, Dict, List

from core.ontology import (
    ArchitectureGraph, Subsystem, Interface, SubsystemType, InterfaceType,
    EnvironmentalRequirements, PerformanceRequirements
)
from core.models import RequirementSpec
from templates.template_system import DeviceTemplate, TemplateInstantiator, RuleAction


# ============================================================================
# Architecture Builder
# ============================================================================

class ArchitectureBuilder:
    """Builds architecture graph from template and user answers"""
    
    def __init__(self, template: DeviceTemplate):
        self.template = template
        self.instantiator = TemplateInstantiator(template)
        self.graph: Optional[ArchitectureGraph] = None
    
    def build_initial_graph(self) -> ArchitectureGraph:
        """Build initial architecture graph from template baseline"""
        graph = ArchitectureGraph(
            device_type=self.template.device_type,
            description=self.template.description
        )
        
        # Add subsystems from template
        for subsystem_name, subsystem_template in self.template.subsystems.items():
            subsystem = Subsystem(
                type=SubsystemType(subsystem_name) if subsystem_name in [s.value for s in SubsystemType] else SubsystemType.COMPUTE,
                required_functions=subsystem_template.required_functions.copy(),
                baseline_constraints=deepcopy(subsystem_template.baseline_constraints),
                notes=subsystem_template.notes
            )
            graph.add_subsystem(subsystem_name, subsystem)
        
        # Add required interfaces
        for interface_name in self.template.required_interfaces:
            try:
                interface_type = InterfaceType(interface_name)
                interface = Interface(type=interface_type, required=True)
                graph.add_interface(interface)
            except ValueError:
                print(f"Warning: Unknown interface type: {interface_name}")
        
        self.graph = graph
        return graph
    
    def add_answer(self, question_id: str, answer: Any):
        """Add user answer and update graph"""
        self.instantiator.add_answer(question_id, answer)
    
    def apply_rules(self) -> ArchitectureGraph:
        """Apply template rules based on current answers"""
        if not self.graph:
            self.build_initial_graph()
        
        modifications = self.instantiator.apply_rules()
        
        # Apply constraint updates
        for action in modifications['constraint_updates']:
            self._apply_constraint_update(action)
        
        # Add subsystems
        for action in modifications['subsystems_to_add']:
            self._add_subsystem(action)
        
        # Remove subsystems
        for action in modifications['subsystems_to_remove']:
            self._remove_subsystem(action)
        
        return self.graph
    
    def _apply_constraint_update(self, action: RuleAction):
        """Apply a constraint update action"""
        if not action.subsystem or action.subsystem not in self.graph.subsystems:
            return
        
        subsystem = self.graph.subsystems[action.subsystem]
        
        if not action.field:
            return
        
        # Navigate nested fields (e.g., "peripherals.pwm_timers")
        field_parts = action.field.split('.')
        target = subsystem.baseline_constraints
        
        for part in field_parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        
        final_field = field_parts[-1]
        
        # Apply operation
        if action.operation == "set":
            target[final_field] = action.value
        elif action.operation == "add":
            current = target.get(final_field, 0)
            target[final_field] = current + action.value
        elif action.operation == "multiply":
            current = target.get(final_field, 1)
            target[final_field] = current * action.value
    
    def _add_subsystem(self, action: RuleAction):
        """Add a new subsystem"""
        if not action.subsystem or action.subsystem in self.graph.subsystems:
            return
        
        subsystem_data = action.value or {}
        subsystem = Subsystem(
            type=SubsystemType(action.subsystem) if action.subsystem in [s.value for s in SubsystemType] else SubsystemType.COMPUTE,
            required_functions=subsystem_data.get('required_functions', []),
            baseline_constraints=subsystem_data.get('baseline_constraints', {})
        )
        
        self.graph.add_subsystem(action.subsystem, subsystem)
    
    def _remove_subsystem(self, action: RuleAction):
        """Remove a subsystem"""
        if action.subsystem and action.subsystem in self.graph.subsystems:
            del self.graph.subsystems[action.subsystem]
    
    def get_graph(self) -> Optional[ArchitectureGraph]:
        """Get current architecture graph"""
        return self.graph


# ============================================================================
# Constraint Compiler
# ============================================================================

class ConstraintCompiler:
    """
    Compiles ArchitectureGraph into RequirementSpec for deterministic solver.
    
    This is the bridge between high-level architecture and low-level constraints.
    
    NEW: Includes intelligent constraint optimization using LLM.
    """
    
    def __init__(self, use_intelligent_optimization: bool = True):
        """
        Initialize compiler.
        
        Args:
            use_intelligent_optimization: Enable LLM-driven constraint optimization
        """
        self.use_intelligent_optimization = use_intelligent_optimization
        
        if use_intelligent_optimization:
            try:
                from architecture.intelligent_optimizer import IntelligentConstraintOptimizer
                self.optimizer = IntelligentConstraintOptimizer()
            except Exception as e:
                import traceback
                print(f"Warning: Intelligent optimizer init failed: {e}")
                traceback.print_exc()
                self.optimizer = None
        else:
            self.optimizer = None
    
    def compile(
        self,
        graph: ArchitectureGraph,
        user_requirements: Optional[Dict[str, Any]] = None,
        template_context: Optional[Dict[str, Any]] = None
    ) -> "RequirementSpec":
        """
        Compile architecture graph into requirement spec.
        
        Args:
            graph: Architecture graph with subsystems and constraints
            user_requirements: Optional user requirements for optimization
            template_context: Optional template context for optimization
            
        Returns:
            RequirementSpec for deterministic solver
        """
        spec = RequirementSpec()
        
        # Extract compute subsystem constraints (primary)
        if 'compute' in graph.subsystems:
            self._compile_compute_constraints(graph.subsystems['compute'], spec)
        
        # Extract power constraints
        if 'power' in graph.subsystems:
            self._compile_power_constraints(graph.subsystems['power'], spec)
        
        # Extract communication constraints
        if 'communication' in graph.subsystems:
            self._compile_communication_constraints(graph.subsystems['communication'], spec)
        
        # Extract environmental requirements
        if graph.environmental_requirements:
            self._compile_environmental_constraints(graph.environmental_requirements, spec)
        
        # Extract performance requirements
        if graph.performance_requirements:
            self._compile_performance_constraints(graph.performance_requirements, spec)
        
        # Extract interface requirements
        self._compile_interface_constraints(graph.interfaces, spec)
        
        # Add additional constraints
        for key, value in graph.additional_constraints.items():
            if not hasattr(spec, key):
                setattr(spec, key, value)
        
        # INTELLIGENT OPTIMIZATION (NEW!)
        if self.optimizer and user_requirements and template_context:
            spec = self._apply_intelligent_optimization(
                spec, user_requirements, template_context
            )
        
        return spec
    
    def _apply_intelligent_optimization(
        self,
        spec: "RequirementSpec",
        user_requirements: Dict[str, Any],
        template_context: Dict[str, Any]
    ) -> "RequirementSpec":
        """Apply intelligent constraint optimization"""
        
        # Convert spec to dict for optimization
        baseline_constraints = {
            "core_arch": getattr(spec, 'core', None),
            "min_flash_kb": getattr(spec, 'flash_kb_min', None),
            "min_sram_kb": getattr(spec, 'sram_kb_min', None),
            "min_mhz": getattr(spec, 'min_mhz', None),
            "peripherals_min": getattr(spec, 'peripherals_min', {}),
            "has_fpu": getattr(spec, 'has_fpu', False),
            "has_dsp": getattr(spec, 'has_dsp', False)
        }
        
        # Remove None values
        baseline_constraints = {k: v for k, v in baseline_constraints.items() if v is not None}
        
        # Optimize
        result = self.optimizer.optimize_constraints(
            baseline_constraints=baseline_constraints,
            user_requirements=user_requirements,
            template_context=template_context
        )
        
        # Apply optimizations back to spec
        optimized = result.optimized_constraints
        
        if 'core_arch' in optimized:
            spec.core = optimized['core_arch']
        if 'min_flash_kb' in optimized:
            spec.flash_kb_min = optimized['min_flash_kb']
        if 'min_sram_kb' in optimized:
            spec.sram_kb_min = optimized['min_sram_kb']
        if 'min_mhz' in optimized:
            spec.min_mhz = optimized['min_mhz']
        if 'peripherals_min' in optimized:
            spec.peripherals_min = optimized['peripherals_min']
        if 'has_fpu' in optimized:
            spec.has_fpu = optimized['has_fpu']
        if 'has_dsp' in optimized:
            spec.has_dsp = optimized['has_dsp']
        
        # Store optimization metadata
        spec.optimization_applied = True
        spec.optimization_confidence = result.confidence_score
        spec.optimizations = [
            {
                "field": opt.field,
                "original": opt.original_value,
                "optimized": opt.optimized_value,
                "reasoning": opt.reasoning
            }
            for opt in result.optimizations
        ]
        
        return spec
    
    def _compile_compute_constraints(self, subsystem: Subsystem, spec: "RequirementSpec"):
        """Compile compute subsystem constraints"""
        constraints = subsystem.baseline_constraints
        
        # Core architecture
        if 'core_arch' in constraints:
            spec.core = constraints['core_arch']
        
        # Clock speed
        if 'min_mhz' in constraints:
            spec.min_mhz = constraints['min_mhz']
        
        # Memory
        if 'min_flash_kb' in constraints:
            spec.flash_kb_min = constraints['min_flash_kb']
        if 'min_sram_kb' in constraints:
            spec.sram_kb_min = constraints['min_sram_kb']
        
        # Peripherals
        if 'peripherals' in constraints:
            peripherals = constraints['peripherals']
            spec.peripherals_min = peripherals
        
        # Features
        if 'has_fpu' in constraints:
            spec.has_fpu = constraints['has_fpu']
        if 'has_dsp' in constraints:
            spec.has_dsp = constraints['has_dsp']
        
        # Power profile
        if 'power_profile' in constraints:
            spec.power_profile = constraints['power_profile']
    
    def _compile_power_constraints(self, subsystem: Subsystem, spec: "RequirementSpec"):
        """Compile power subsystem constraints"""
        constraints = subsystem.baseline_constraints
        
        if 'input_voltage_range' in constraints:
            vrange = constraints['input_voltage_range']
            spec.voltage_min = vrange[0]
            spec.voltage_max = vrange[1]
        
        if 'battery_powered' in constraints:
            spec.battery_powered = constraints['battery_powered']
    
    def _compile_communication_constraints(self, subsystem: Subsystem, spec: "RequirementSpec"):
        """Compile communication subsystem constraints"""
        constraints = subsystem.baseline_constraints
        
        if 'wireless_protocol' in constraints:
            spec.wireless_protocol = constraints['wireless_protocol']
    
    def _compile_environmental_constraints(self, env: EnvironmentalRequirements, spec: "RequirementSpec"):
        """Compile environmental requirements"""
        spec.temp_min = env.temp_min_c
        spec.temp_max = env.temp_max_c
        spec.environment_type = env.environment_type.value
    
    def _compile_performance_constraints(self, perf: PerformanceRequirements, spec: "RequirementSpec"):
        """Compile performance requirements"""
        spec.power_profile = perf.power_profile.value
        spec.performance_class = perf.performance_class.value
    
    def _compile_interface_constraints(self, interfaces: List[Interface], spec: "RequirementSpec"):
        """Compile interface requirements into peripheral constraints"""
        if not hasattr(spec, 'peripherals_min'):
            spec.peripherals_min = {}
        
        for interface in interfaces:
            if not interface.required:
                continue
            
            # Map interface types to peripheral requirements
            interface_map = {
                InterfaceType.CAN: 'can',
                InterfaceType.CAN_FD: 'can_fd',
                InterfaceType.USB_FS: 'usb_fs',
                InterfaceType.USB_HS: 'usb_hs',
                InterfaceType.ETHERNET: 'ethernet',
                InterfaceType.SDMMC: 'sdmmc',
                InterfaceType.I2C: 'i2c',
                InterfaceType.SPI: 'spi',
                InterfaceType.UART: 'uart',
            }
            
            if interface.type in interface_map:
                peripheral_name = interface_map[interface.type]
                current_count = spec.peripherals_min.get(peripheral_name, 0)
                spec.peripherals_min[peripheral_name] = max(current_count, interface.count)


# ============================================================================
# Helper Functions
# ============================================================================

def build_architecture_from_template(
    template: DeviceTemplate,
    answers: Dict[str, Any]
) -> ArchitectureGraph:
    """
    Build architecture graph from template and answers.
    
    Args:
        template: Device template
        answers: Dict of question_id -> answer
        
    Returns:
        Complete architecture graph
    """
    builder = ArchitectureBuilder(template)
    builder.build_initial_graph()
    
    for question_id, answer in answers.items():
        builder.add_answer(question_id, answer)
    
    return builder.apply_rules()


def compile_architecture_to_spec(graph: ArchitectureGraph) -> "RequirementSpec":
    """
    Compile architecture graph to requirement spec.
    
    Args:
        graph: Architecture graph
        
    Returns:
        RequirementSpec for solver
    """
    compiler = ConstraintCompiler()
    return compiler.compile(graph)
