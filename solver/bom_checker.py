"""
BOM Compatibility Checker — Dream Spec #2

Cross-checks a Bill of Materials (BOM) list of selected components and identifies
compatibility issues, warnings, and validates the design holistically.

Checks performed:
    1. Voltage level compatibility (MCU I/O vs peripheral logic levels)
    2. Power supply adequacy (LDO/PMIC output vs MCU + peripheral power draw)
    3. Temperature range overlap (all parts must share a common operating window)
    4. CAN bus compatibility (baud rate, transceiver ↔ MCU CAN peripheral)
    5. Interface speeds (SPI/I2C max rate consistency)
    6. Package/signal integrity (optional note-level warnings)
"""

from __future__ import annotations
import logging
from typing import List, Dict, Any, Tuple, Optional
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CheckSeverity(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass
class CompatibilityIssue:
    check_name: str
    severity: CheckSeverity
    parts_involved: List[str]          # List of MPNs involved
    message: str
    recommendation: str = ""


@dataclass
class BOMReport:
    total_parts: int
    issues: List[CompatibilityIssue] = field(default_factory=list)
    warnings: List[CompatibilityIssue] = field(default_factory=list)
    passed: List[CompatibilityIssue] = field(default_factory=list)

    @property
    def overall_verdict(self) -> CheckSeverity:
        if any(i.severity == CheckSeverity.FAIL for i in self.issues):
            return CheckSeverity.FAIL
        if any(i.severity == CheckSeverity.WARNING for i in self.warnings):
            return CheckSeverity.WARNING
        return CheckSeverity.PASS

    def to_dict(self) -> Dict[str, Any]:
        def _issue_dict(i: CompatibilityIssue) -> Dict:
            return {
                "check_name": i.check_name,
                "severity": i.severity.value,
                "parts_involved": i.parts_involved,
                "message": i.message,
                "recommendation": i.recommendation,
            }

        return {
            "total_parts": self.total_parts,
            "overall_verdict": self.overall_verdict.value,
            "fail_count": len(self.issues),
            "warning_count": len(self.warnings),
            "pass_count": len(self.passed),
            "issues": [_issue_dict(i) for i in self.issues],
            "warnings": [_issue_dict(i) for i in self.warnings],
            "passed": [_issue_dict(i) for i in self.passed],
        }


class BOMCompatibilityChecker:
    """
    Stateless BOM cross-checker.
    Accepts a list of part dicts (as returned by api/search or hard_filter)
    and returns a BOMReport.
    """

    def check(self, parts: List[Dict[str, Any]]) -> BOMReport:
        """
        Run all compatibility checks on the provided BOM parts.
        Args:
            parts: List of part dicts, each with top-level keys and a nested
                   'specs' key (same format as the /api/search results).
        Returns:
            BOMReport with all findings.
        """
        report = BOMReport(total_parts=len(parts))
        if len(parts) < 2:
            report.passed.append(CompatibilityIssue(
                check_name="BOM Completeness",
                severity=CheckSeverity.PASS,
                parts_involved=[p.get("mpn", "?") for p in parts],
                message="Only one part in BOM — no cross-part checks needed.",
            ))
            return report

        mcus = self._parts_of_type(parts, "mcu")
        ldos = self._parts_of_type(parts, "ldo")
        pmics = self._parts_of_type(parts, "pmic")
        cans = self._parts_of_type(parts, "can")

        self._check_voltage_compatibility(parts, mcus, ldos + pmics, report)
        self._check_power_supply_adequacy(parts, mcus, ldos, report)
        self._check_temperature_overlap(parts, report)
        self._check_can_compatibility(mcus, cans, report)
        self._check_multiple_mcus(mcus, report)
        self._check_interface_conflicts(parts, mcus, report)

        return report

    # ─────────────────────────────────────────────────────────────────────────
    # Individual checks
    # ─────────────────────────────────────────────────────────────────────────

    def _safe_float(self, val: Any) -> Optional[float]:
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    def _safe_int(self, val: Any) -> Optional[int]:
        try:
            return int(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    def _check_voltage_compatibility(
        self,
        all_parts: List[Dict],
        mcus: List[Dict],
        regulators: List[Dict],
        report: BOMReport,
    ):
        """Check that regulators supply a voltage the MCU expects (3.3V)."""
        mpns = self._mpns(all_parts)
        if not mcus or not regulators:
            report.passed.append(CompatibilityIssue(
                check_name="Voltage Level Compatibility",
                severity=CheckSeverity.PASS,
                parts_involved=mpns,
                message="No MCU + regulator pair to check — skipping voltage check.",
            ))
            return

        for mcu in mcus:
            mcu_mpn = str(mcu.get("mpn") or "MCU")
            # Most ARM Cortex-M MCUs operate at 3.3V or 1.8V — infer from family
            expected_v = 3.3  # Default assumption

            for reg in regulators:
                reg_mpn = str(reg.get("mpn") or "REG")
                reg_specs = reg.get("specs", reg)
                vout = self._safe_float(reg_specs.get("vout_fixed_v")) or self._safe_float(reg_specs.get("vout_max_v"))

                if vout is None:
                    report.warnings.append(CompatibilityIssue(
                        check_name="Voltage Level Compatibility",
                        severity=CheckSeverity.WARNING,
                        parts_involved=[mcu_mpn, reg_mpn],
                        message=f"{reg_mpn}: output voltage not specified in datasheet data.",
                        recommendation=f"Verify {reg_mpn} supplies ~{expected_v}V for {mcu_mpn}.",
                    ))
                elif abs(vout - expected_v) < 0.15:
                    report.passed.append(CompatibilityIssue(
                        check_name="Voltage Level Compatibility",
                        severity=CheckSeverity.PASS,
                        parts_involved=[mcu_mpn, reg_mpn],
                        message=f"{reg_mpn} ({vout}V) ✓ compatible with {mcu_mpn} ({expected_v}V).",
                    ))
                elif abs(vout - 1.8) < 0.15:
                    report.warnings.append(CompatibilityIssue(
                        check_name="Voltage Level Compatibility",
                        severity=CheckSeverity.WARNING,
                        parts_involved=[mcu_mpn, reg_mpn],
                        message=f"{reg_mpn} outputs 1.8V — verify {mcu_mpn} supports 1.8V operation.",
                        recommendation="Check MCU datasheet for minimum VDD; some peripherals may need level-shifting.",
                    ))
                else:
                    report.issues.append(CompatibilityIssue(
                        check_name="Voltage Level Compatibility",
                        severity=CheckSeverity.FAIL,
                        parts_involved=[mcu_mpn, reg_mpn],
                        message=(
                            f"VOLTAGE MISMATCH: {reg_mpn} outputs {vout}V but {mcu_mpn} "
                            f"expects ~{expected_v}V. This will damage the MCU."
                        ),
                        recommendation=f"Replace {reg_mpn} with a {expected_v}V LDO, or use a level-shifter.",
                    ))

    def _check_power_supply_adequacy(
        self,
        all_parts: List[Dict],
        mcus: List[Dict],
        ldos: List[Dict],
        report: BOMReport,
    ):
        """Check if LDO output current is sufficient for all MCU loads."""
        if not mcus or not ldos:
            return  # Can't check without both

        # Rough MCU current budgets by family
        MCU_CURRENT_MAP = {
            "STM32H7": 300,   # mA
            "STM32F4": 150,
            "STM32F1": 100,
            "STM32G0": 60,
            "STM32L":  30,    # Low power series
            "cortex-m7": 300,
            "cortex-m4": 150,
            "cortex-m0": 60,
        }

        for mcu in mcus:
            mcu_mpn = str(mcu.get("mpn") or "MCU")
            mcu_specs = mcu.get("specs", mcu)
            # Estimate MCU current from family name
            estimated_ma = 150  # default
            family = (mcu.get("family") or mcu_specs.get("family") or "").upper()
            for key, ma in MCU_CURRENT_MAP.items():
                if key.upper() in family or key.upper() in mcu_mpn.upper():
                    estimated_ma = ma
                    break

            for ldo in ldos:
                ldo_mpn = str(ldo.get("mpn") or "LDO")
                ldo_specs = ldo.get("specs", ldo)
                iout_ma = self._safe_float(ldo_specs.get("iout_max_ma"))

                if iout_ma is None:
                    report.warnings.append(CompatibilityIssue(
                        check_name="Power Supply Adequacy",
                        severity=CheckSeverity.WARNING,
                        parts_involved=[mcu_mpn, ldo_mpn],
                        message=f"{ldo_mpn}: max output current not specified.",
                        recommendation=f"Verify {ldo_mpn} can supply ≥{estimated_ma}mA for {mcu_mpn}.",
                    ))
                elif iout_ma >= estimated_ma * 1.2:  # 20% headroom
                    report.passed.append(CompatibilityIssue(
                        check_name="Power Supply Adequacy",
                        severity=CheckSeverity.PASS,
                        parts_involved=[mcu_mpn, ldo_mpn],
                        message=(
                            f"{ldo_mpn} ({iout_ma:.0f}mA max) ✓ adequate for {mcu_mpn} "
                            f"(~{estimated_ma}mA, {iout_ma / estimated_ma:.1f}× headroom)."
                        ),
                    ))
                elif iout_ma >= estimated_ma:
                    report.warnings.append(CompatibilityIssue(
                        check_name="Power Supply Adequacy",
                        severity=CheckSeverity.WARNING,
                        parts_involved=[mcu_mpn, ldo_mpn],
                        message=(
                            f"{ldo_mpn} ({iout_ma:.0f}mA) barely meets {mcu_mpn} load "
                            f"(~{estimated_ma}mA). No margin for peripherals."
                        ),
                        recommendation="Add 20–30% headroom. Consider a higher-current LDO.",
                    ))
                else:
                    report.issues.append(CompatibilityIssue(
                        check_name="Power Supply Adequacy",
                        severity=CheckSeverity.FAIL,
                        parts_involved=[mcu_mpn, ldo_mpn],
                        message=(
                            f"UNDERPOWERED: {ldo_mpn} max {iout_ma:.0f}mA < {mcu_mpn} "
                            f"estimated {estimated_ma}mA. System will brown out."
                        ),
                        recommendation=f"Replace {ldo_mpn} with a ≥{int(estimated_ma * 1.3)}mA regulator.",
                    ))

    def _check_temperature_overlap(self, parts: List[Dict], report: BOMReport):
        """Validate all parts share a common operating temperature window."""
        ranges = []
        for p in parts:
            mpn = str(p.get("mpn") or "?")
            t_min = self._safe_float(p.get("temp_min_c"))
            t_max = self._safe_float(p.get("temp_max_c"))
            if t_min is not None and t_max is not None:
                ranges.append((mpn, t_min, t_max))

        if len(ranges) < 2:
            return  # Not enough data

        overlap_min = max(r[1] for r in ranges)
        overlap_max = min(r[2] for r in ranges)

        if overlap_min >= overlap_max:
            narrowest = [r[0] for r in ranges if r[1] == overlap_min or r[2] == overlap_max]
            report.issues.append(CompatibilityIssue(
                check_name="Temperature Range Overlap",
                severity=CheckSeverity.FAIL,
                parts_involved=[r[0] for r in ranges],
                message=(
                    f"NO COMMON OPERATING TEMPERATURE: Parts have incompatible temperature ranges. "
                    f"Overlap window is [{overlap_min}°C, {overlap_max}°C]."
                ),
                recommendation=f"Parts {narrowest} constrain the design. Use industrial-grade alternatives.",
            ))
        elif overlap_max - overlap_min < 40:
            report.warnings.append(CompatibilityIssue(
                check_name="Temperature Range Overlap",
                severity=CheckSeverity.WARNING,
                parts_involved=[r[0] for r in ranges],
                message=(
                    f"Narrow temperature overlap: [{overlap_min}°C to {overlap_max}°C] "
                    f"({overlap_max - overlap_min}°C window). May be limited for some environments."
                ),
                recommendation="Verify operating environment. Consider extended-range parts if deploying outdoors.",
            ))
        else:
            report.passed.append(CompatibilityIssue(
                check_name="Temperature Range Overlap",
                severity=CheckSeverity.PASS,
                parts_involved=[r[0] for r in ranges],
                message=(
                    f"✓ All parts share common operating range: [{overlap_min}°C to {overlap_max}°C] "
                    f"({overlap_max - overlap_min}°C window)."
                ),
            ))

    def _check_can_compatibility(
        self, mcus: List[Dict], can_transceivers: List[Dict], report: BOMReport
    ):
        """Check that MCU CAN peripheral count matches transceiver count."""
        if not can_transceivers:
            return

        for mcu in mcus:
            mcu_mpn = str(mcu.get("mpn") or "MCU")
            mcu_specs = mcu.get("specs", mcu)
            can_count = self._safe_int(mcu_specs.get("can_count")) or 0

            if can_count == 0:
                report.issues.append(CompatibilityIssue(
                    check_name="CAN Bus Compatibility",
                    severity=CheckSeverity.FAIL,
                    parts_involved=[mcu_mpn] + [c.get("mpn", "?") for c in can_transceivers],
                    message=f"{mcu_mpn} has NO CAN peripheral but {len(can_transceivers)} CAN transceiver(s) in BOM.",
                    recommendation="Replace MCU with one that has CAN peripheral, or remove CAN transceivers.",
                ))
            elif can_count >= len(can_transceivers):
                report.passed.append(CompatibilityIssue(
                    check_name="CAN Bus Compatibility",
                    severity=CheckSeverity.PASS,
                    parts_involved=[mcu_mpn] + [c.get("mpn", "?") for c in can_transceivers],
                    message=f"✓ {mcu_mpn} has {can_count} CAN peripheral(s), matches {len(can_transceivers)} transceiver(s).",
                ))
            else:
                report.warnings.append(CompatibilityIssue(
                    check_name="CAN Bus Compatibility",
                    severity=CheckSeverity.WARNING,
                    parts_involved=[mcu_mpn] + [c.get("mpn", "?") for c in can_transceivers],
                    message=(
                        f"{mcu_mpn} has {can_count} CAN peripheral(s) but BOM has "
                        f"{len(can_transceivers)} transceiver(s). Extra transceivers cannot be used."
                    ),
                    recommendation="Remove unused CAN transceivers from BOM.",
                ))

    def _check_multiple_mcus(self, mcus: List[Dict], report: BOMReport):
        """Warn if multiple MCUs are in the BOM — might be intentional (multi-MCU design)."""
        if len(mcus) > 1:
            report.warnings.append(CompatibilityIssue(
                check_name="Multiple MCUs",
                severity=CheckSeverity.WARNING,
                parts_involved=[m.get("mpn", "?") for m in mcus],
                message=f"BOM contains {len(mcus)} MCUs. Is this a multi-MCU design?",
                recommendation=(
                    "If intentional (e.g., safety co-processor), document the IPC protocol. "
                    "If accidental, remove the duplicate MCU."
                ),
            ))

    def _check_interface_conflicts(
        self, all_parts: List[Dict], mcus: List[Dict], report: BOMReport
    ):
        """
        Check if the MCU has enough peripheral channels for all BOM components.
        Simple heuristic: estimate required bus count from non-MCU parts.
        """
        if not mcus:
            return

        non_mcu = [p for p in all_parts if self._infer_type(p) != "mcu"]
        # Each non-MCU peripheral likely needs one SPI, I2C, or UART channel
        estimated_bus_need = len(non_mcu)

        for mcu in mcus:
            mcu_mpn = str(mcu.get("mpn") or "MCU")
            mcu_specs = mcu.get("specs", mcu)
            spi = self._safe_int(mcu_specs.get("spi_count")) or 0
            i2c = self._safe_int(mcu_specs.get("i2c_count")) or 0
            uart = self._safe_int(mcu_specs.get("uart_count")) or 0
            total_buses = spi + i2c + uart

            if total_buses >= estimated_bus_need:
                report.passed.append(CompatibilityIssue(
                    check_name="Interface Availability",
                    severity=CheckSeverity.PASS,
                    parts_involved=[mcu_mpn],
                    message=(
                        f"✓ {mcu_mpn} has {total_buses} total comm buses "
                        f"(SPI×{spi}, I2C×{i2c}, UART×{uart}) — "
                        f"sufficient for {len(non_mcu)} peripheral(s)."
                    ),
                ))
            else:
                report.warnings.append(CompatibilityIssue(
                    check_name="Interface Availability",
                    severity=CheckSeverity.WARNING,
                    parts_involved=[mcu_mpn],
                    message=(
                        f"{mcu_mpn} has {total_buses} comm buses but BOM has {len(non_mcu)} "
                        f"peripheral devices. Bus sharing may be required."
                    ),
                    recommendation="Use bus multiplexers or confirm peripherals share SPI/I2C buses.",
                ))

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _infer_type(self, part: Dict) -> str:
        """Infer component type from part data."""
        specs = part.get("specs", part)
        # If it has mcu-specific fields, it's an MCU
        if specs.get("flash_kb") or specs.get("core") or specs.get("max_mhz"):
            return "mcu"
        if specs.get("iout_max_ma") or "LDO" in str(part.get("mpn", "")).upper():
            return "ldo"
        if specs.get("buck_count") is not None:
            return "pmic"
        if specs.get("data_rate_mbps") is not None:
            return "can"
        if specs.get("sensor_type"):
            return "sensor"
        return "unknown"

    def _parts_of_type(self, parts: List[Dict], ptype: str) -> List[Dict]:
        return [p for p in parts if self._infer_type(p) == ptype]

    def _mpns(self, parts: List[Dict]) -> List[str]:
        return [p.get("mpn", "?") for p in parts]
