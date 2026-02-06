"""
Validator

Validate extracted fields with type/range checks, cross-source consistency,
and conflict detection.
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from uuid import UUID

from core.models import EvidenceRecord, Conflict, ConflictStatus

logger = logging.getLogger(__name__)


class Validator:
    """Validate extracted fields and detect conflicts"""
    
    def __init__(self):
        """Initialize validator with validation rules"""
        self.field_rules = self._init_field_rules()
        self.conflict_threshold = 0.1  # 10% difference triggers conflict
    
    def _init_field_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize validation rules per field"""
        return {
            'flash_kb': {
                'type': int,
                'min': 4,
                'max': 16384,  # 16MB max
                'required': True,
            },
            'sram_kb': {
                'type': int,
                'min': 1,
                'max': 2048,  # 2MB max
                'required': True,
            },
            'eeprom_kb': {
                'type': int,
                'min': 0,
                'max': 256,
                'required': False,
            },
            'max_mhz': {
                'type': int,
                'min': 1,
                'max': 1000,  # 1GHz max
                'required': True,
            },
            'temp_min_c': {
                'type': int,
                'min': -55,
                'max': 0,
                'required': True,
            },
            'temp_max_c': {
                'type': int,
                'min': 0,
                'max': 150,
                'required': True,
            },
            'pin_count': {
                'type': int,
                'min': 4,
                'max': 500,
                'required': True,
            },
            'can_count': {
                'type': int,
                'min': 0,
                'max': 8,
                'required': False,
            },
            'can_fd_count': {
                'type': int,
                'min': 0,
                'max': 8,
                'required': False,
            },
            'uart_count': {
                'type': int,
                'min': 0,
                'max': 16,
                'required': False,
            },
            'spi_count': {
                'type': int,
                'min': 0,
                'max': 16,
                'required': False,
            },
            'i2c_count': {
                'type': int,
                'min': 0,
                'max': 16,
                'required': False,
            },
            'adc_channels': {
                'type': int,
                'min': 0,
                'max': 64,
                'required': False,
            },
            'timers_count': {
                'type': int,
                'min': 0,
                'max': 32,
                'required': False,
            },
            'vdd_min_v': {
                'type': float,
                'min': 0.8,
                'max': 5.5,
                'required': False,
            },
            'vdd_max_v': {
                'type': float,
                'min': 1.0,
                'max': 6.0,
                'required': False,
            },
            'cost_usd': {
                'type': float,
                'min': 0.01,
                'max': 1000.0,
                'required': False,
            },
        }
    
    def validate_field(
        self,
        field_name: str,
        value: Any,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a single field value.
        
        Args:
            field_name: Field to validate
            value: Value to check
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if field_name not in self.field_rules:
            # Unknown field - allow but log warning
            logger.warning(f"No validation rule for field: {field_name}")
            return True, None
        
        rules = self.field_rules[field_name]
        
        # Type check
        expected_type = rules['type']
        if not isinstance(value, expected_type):
            try:
                # Try to convert
                value = expected_type(value)
            except (ValueError, TypeError):
                return False, f"Invalid type for {field_name}: expected {expected_type.__name__}, got {type(value).__name__}"
        
        # Range check
        if 'min' in rules and value < rules['min']:
            return False, f"{field_name} value {value} below minimum {rules['min']}"
        
        if 'max' in rules and value > rules['max']:
            return False, f"{field_name} value {value} above maximum {rules['max']}"
        
        return True, None
    
    def validate_extraction(
        self,
        extraction: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Validate a complete extraction.
        
        Args:
            extraction: Dict with field_name, normalized_value, etc.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        field_name = extraction.get('field_name')
        normalized_value = extraction.get('normalized_value')
        
        if not field_name:
            errors.append("Missing field_name")
            return False, errors
        
        if normalized_value is None:
            errors.append(f"Missing normalized_value for {field_name}")
            return False, errors
        
        # Validate field value
        is_valid, error = self.validate_field(field_name, normalized_value)
        if not is_valid:
            errors.append(error)
        
        # Check evidence metadata
        if 'page' not in extraction or extraction['page'] is None:
            errors.append(f"Missing page number for {field_name}")
        
        return len(errors) == 0, errors
    
    def validate_part_consistency(
        self,
        part_data: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Validate internal consistency of part data.
        
        Args:
            part_data: Complete part specification
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Temperature range consistency
        temp_min = part_data.get('temp_min_c')
        temp_max = part_data.get('temp_max_c')
        
        if temp_min is not None and temp_max is not None:
            if temp_min >= temp_max:
                errors.append(f"temp_min_c ({temp_min}) must be less than temp_max_c ({temp_max})")
        
        # Voltage range consistency
        vdd_min = part_data.get('vdd_min_v')
        vdd_max = part_data.get('vdd_max_v')
        
        if vdd_min is not None and vdd_max is not None:
            if vdd_min >= vdd_max:
                errors.append(f"vdd_min_v ({vdd_min}) must be less than vdd_max_v ({vdd_max})")
        
        # CAN-FD implies CAN capability
        can_fd_count = part_data.get('can_fd_count', 0)
        can_count = part_data.get('can_count', 0)
        
        if can_fd_count > 0 and can_count == 0:
            # Auto-correct: CAN-FD controllers can do CAN 2.0
            logger.info(f"Auto-correcting: CAN-FD count {can_fd_count} implies CAN count")
            part_data['can_count'] = can_fd_count
        
        # Flash should be >= RAM (sanity check)
        flash_kb = part_data.get('flash_kb', 0)
        sram_kb = part_data.get('sram_kb', 0)
        
        if flash_kb > 0 and sram_kb > 0:
            if sram_kb > flash_kb * 2:  # Allow some flexibility
                errors.append(f"Suspicious: sram_kb ({sram_kb}) much larger than flash_kb ({flash_kb})")
        
        return len(errors) == 0, errors
    
    def detect_conflicts(
        self,
        evidence_list: List[EvidenceRecord],
    ) -> List[Conflict]:
        """
        Detect conflicts across multiple evidence records for same part.
        
        Args:
            evidence_list: List of evidence for same part
        
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        # Group evidence by field_path
        by_field: Dict[str, List[EvidenceRecord]] = {}
        for evidence in evidence_list:
            field_path = evidence.field_path
            if field_path not in by_field:
                by_field[field_path] = []
            by_field[field_path].append(evidence)
        
        # Check each field for conflicts
        for field_path, field_evidence in by_field.items():
            if len(field_evidence) < 2:
                continue  # No conflict possible
            
            # Extract normalized values
            values = []
            for ev in field_evidence:
                if isinstance(ev.normalized_value, dict):
                    value = ev.normalized_value.get('value')
                else:
                    value = ev.normalized_value
                values.append((value, ev))
            
            # Check for conflicts
            if self._has_conflict(values):
                conflict = Conflict(
                    part_id=field_evidence[0].part_id,
                    field_path=field_path,
                    evidence_ids=[ev.id for ev in field_evidence],
                    status=ConflictStatus.OPEN,
                )
                conflicts.append(conflict)
                
                logger.warning(
                    f"Conflict detected for {field_path}: "
                    f"values={[v[0] for v in values]}"
                )
        
        return conflicts
    
    def _has_conflict(
        self,
        values: List[Tuple[Any, EvidenceRecord]],
    ) -> bool:
        """
        Check if values conflict (differ beyond threshold).
        
        Args:
            values: List of (value, evidence) tuples
        
        Returns:
            True if conflict detected
        """
        if not values:
            return False
        
        # Get unique values
        unique_values = set(v[0] for v in values)
        
        if len(unique_values) == 1:
            return False  # All same
        
        # For numeric values, check if difference exceeds threshold
        try:
            numeric_values = [float(v[0]) for v in values]
            min_val = min(numeric_values)
            max_val = max(numeric_values)
            
            if min_val == 0:
                # Use absolute difference
                if max_val > 0:
                    return True
            else:
                # Use relative difference
                relative_diff = (max_val - min_val) / min_val
                if relative_diff > self.conflict_threshold:
                    return True
            
            return False
        
        except (ValueError, TypeError):
            # Non-numeric values - any difference is a conflict
            return len(unique_values) > 1
    
    def calculate_confidence(
        self,
        extraction: Dict[str, Any],
        source_type: str,
    ) -> float:
        """
        Calculate confidence score for an extraction.
        
        Args:
            extraction: Extraction data
            source_type: Source type (mfg_pdf, mfg_html, etc.)
        
        Returns:
            Confidence score (0.0 to 1.0)
        """
        base_confidence = {
            'mfg_pdf': 0.9,
            'mfg_html': 0.85,
            'dist_html': 0.6,
            'other': 0.5,
        }.get(source_type, 0.5)
        
        # Adjust based on extraction method
        source = extraction.get('source', 'text')
        
        if source == 'table':
            # Tables are more reliable
            confidence = base_confidence * 1.0
        elif source == 'ocr':
            # OCR is less reliable
            confidence = base_confidence * 0.7
        else:
            # Text extraction
            confidence = base_confidence * 0.9
        
        # Adjust based on pattern match quality
        pattern_used = extraction.get('pattern_used')
        if pattern_used:
            # Specific pattern match is more reliable
            confidence *= 1.05
        
        # Cap at 1.0
        return min(confidence, 1.0)
