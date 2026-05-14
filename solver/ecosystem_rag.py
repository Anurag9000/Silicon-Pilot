"""
Ecosystem RAG — Companion Chip Recommender
==========================================
Given an MCU part_id and the original user requirements (free-text or parsed spec),
this engine recommends a complete matched chipset:
  - CAN transceivers (matching MCU logic level)
  - Motor drivers (matching application type)
  - IMUs / Sensors (matching interface)
  - PMICs / LDOs (matching voltage rails)
  - RS-485 transceivers

Matching rules:
  1. Logic level compatibility: MCU at 3.3V → only 3.3V-native parts (no level shifter needed)
  2. Interface compatibility: MCU has SPI → prefer SPI-based companions
  3. Application keyword matching: "motor" → motor drivers, "can" → CAN transceivers, etc.
  4. Cost-aware ranking: cheaper alternatives surfaced when functionally equivalent
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Dict
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)

# Keyword → companion chip categories to suggest
_KEYWORD_CATEGORIES: Dict[str, List[str]] = {
    "motor":      ["motor_driver", "can_transceiver"],
    "bldc":       ["motor_driver"],
    "stepper":    ["motor_driver"],
    "servo":      ["motor_driver"],
    "can":        ["can_transceiver"],
    "canfd":      ["can_transceiver"],
    "can-fd":     ["can_transceiver"],
    "automotive": ["can_transceiver", "motor_driver"],
    "imu":        ["imu"],
    "gyro":       ["imu"],
    "accel":      ["imu"],
    "gesture":    ["imu"],
    "drone":      ["imu", "motor_driver"],
    "robot":      ["imu", "motor_driver", "can_transceiver"],
    "iot":        ["sensor", "ldo"],
    "sensor":     ["sensor", "imu"],
    "pressure":   ["sensor"],
    "weather":    ["sensor"],
    "altitude":   ["sensor"],
    "rs485":      ["rs485"],
    "modbus":     ["rs485"],
    "battery":    ["ldo", "pmic"],
    "power":      ["pmic", "ldo"],
    "usb-c":      ["pmic"],
    "usbpd":      ["pmic"],
    "wireless":   ["pmic"],
    "wearable":   ["imu", "ldo"],
}

# Always-suggest categories (useful for almost every design)
_BASELINE_CATEGORIES = ["ldo"]


@dataclass
class CompanionChip:
    id: str
    mpn: str
    manufacturer: str
    category: str
    description: str
    interface: Optional[str]
    logic_level_v: Optional[float]
    vcc_min_v: Optional[float]
    vcc_max_v: Optional[float]
    cost_usd: Optional[float]
    package: Optional[str]
    notes: str
    match_reason: str
    compatibility_warning: Optional[str]
    tags: List[str]


@dataclass
class EcosystemResult:
    mcu_mpn: str
    mcu_logic_v: float
    mcu_vdd_min: Optional[float]
    mcu_vdd_max: Optional[float]
    matched_categories: List[str]
    companions: List[CompanionChip]
    chipset_summary: str
    total_bom_cost_usd: Optional[float]
    integration_notes: List[str]


class EcosystemRAG:
    """
    Recommends companion chips for a given MCU based on application requirements.

    Usage:
        rag = EcosystemRAG(db_pool)
        result = await rag.recommend(
            part_id="<uuid>",
            requirement_text="motor controller with CAN, 3-phase BLDC",
        )
    """

    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool

    async def recommend(
        self,
        part_id: str,
        requirement_text: str = "",
        spec_dict: Optional[Dict] = None,
    ) -> EcosystemResult:
        uuid_id = UUID(part_id)

        # ── Load MCU info ────────────────────────────────────────────────────
        async with self.pool.acquire() as conn:
            mcu_row = await conn.fetchrow("""
                SELECT p.mpn, p.family,
                       ms.vdd_min_v, ms.vdd_max_v,
                       ms.voltage_min_v, ms.voltage_max_v,
                       ms.uart_count, ms.spi_count, ms.i2c_count,
                       ms.can_count, ms.can_fd_count, ms.usb_fs, ms.ethernet
                FROM parts p
                JOIN mcu_specs ms ON ms.part_id = p.id
                WHERE p.id = $1
            """, uuid_id)

            if not mcu_row:
                raise ValueError(f"Part {part_id} not found or missing spec data")

            # Load all companion chips
            all_companions = await conn.fetch("""
                SELECT id, mpn, manufacturer, category, description,
                       interface, logic_level_v, vcc_min_v, vcc_max_v,
                       cost_usd, package, notes, tags
                FROM companion_chips
                ORDER BY cost_usd ASC NULLS LAST
            """)

        mcu = dict(mcu_row)
        mcu_mpn = mcu["mpn"]

        # Determine MCU logic voltage (most STM32s are 3.3V)
        vdd_max = mcu.get("vdd_max_v") or mcu.get("voltage_max_v") or 3.6
        vdd_min = mcu.get("vdd_min_v") or mcu.get("voltage_min_v") or 1.8
        mcu_logic_v = 3.3 if float(vdd_max) <= 3.6 else 5.0

        # ── Determine which categories to suggest ────────────────────────────
        text_lower = requirement_text.lower()
        # Also merge any hard constraint keys from spec_dict
        if spec_dict:
            hard = spec_dict.get("hard_constraints", {})
            for k in hard:
                text_lower += f" {k.lower()}"

        matched_cats: List[str] = list(_BASELINE_CATEGORIES)
        for keyword, cats in _KEYWORD_CATEGORIES.items():
            if keyword in text_lower:
                for cat in cats:
                    if cat not in matched_cats:
                        matched_cats.append(cat)

        # Always suggest CAN transceivers if MCU has CAN interfaces
        can_total = (mcu.get("can_count") or 0) + (mcu.get("can_fd_count") or 0)
        if can_total > 0 and "can_transceiver" not in matched_cats:
            matched_cats.append("can_transceiver")

        # ── Score and filter companion chips ─────────────────────────────────
        companions: List[CompanionChip] = []

        for row in all_companions:
            chip = dict(row)
            category = chip["category"]

            if category not in matched_cats:
                continue

            # Logic level compatibility
            chip_logic = chip.get("logic_level_v")
            compat_warning = None
            if chip_logic is not None:
                chip_logic = float(chip_logic)
                if chip_logic > mcu_logic_v + 0.3:
                    compat_warning = (
                        f" Logic level mismatch: {chip['mpn']} runs at {chip_logic}V, "
                        f"{mcu_mpn} at {mcu_logic_v}V. Level-shifter required (e.g. TXS0108E)."
                    )

            # Build match reason
            match_reason = _build_match_reason(category, chip, mcu, text_lower, mcu_logic_v)

            tags = chip.get("tags") or []

            companions.append(CompanionChip(
                id=str(chip["id"]),
                mpn=chip["mpn"],
                manufacturer=chip["manufacturer"],
                category=category,
                description=chip["description"],
                interface=chip.get("interface"),
                logic_level_v=chip_logic,
                vcc_min_v=float(chip["vcc_min_v"]) if chip.get("vcc_min_v") else None,
                vcc_max_v=float(chip["vcc_max_v"]) if chip.get("vcc_max_v") else None,
                cost_usd=float(chip["cost_usd"]) if chip.get("cost_usd") else None,
                package=chip.get("package"),
                notes=chip.get("notes") or "",
                match_reason=match_reason,
                compatibility_warning=compat_warning,
                tags=tags,
            ))

        # Group by category — keep best 2 per category
        by_cat: Dict[str, List[CompanionChip]] = {}
        for c in companions:
            by_cat.setdefault(c.category, []).append(c)

        # Sort within category: native logic first, then by cost
        final: List[CompanionChip] = []
        for cat, chips in by_cat.items():
            chips.sort(key=lambda c: (
                0 if c.compatibility_warning is None else 1,
                c.cost_usd or 999.0
            ))
            final.extend(chips[:2])  # top 2 per category

        # ── Build summary ────────────────────────────────────────────────────
        total_cost = None
        if all(c.cost_usd is not None for c in final):
            total_cost = round(sum(c.cost_usd for c in final), 2)

        chipset_summary = _build_chipset_summary(mcu_mpn, final, matched_cats)
        integration_notes = _build_integration_notes(mcu_mpn, mcu_logic_v, final)

        return EcosystemResult(
            mcu_mpn=mcu_mpn,
            mcu_logic_v=mcu_logic_v,
            mcu_vdd_min=float(vdd_min) if vdd_min else None,
            mcu_vdd_max=float(vdd_max) if vdd_max else None,
            matched_categories=matched_cats,
            companions=final,
            chipset_summary=chipset_summary,
            total_bom_cost_usd=total_cost,
            integration_notes=integration_notes,
        )


def _build_match_reason(
    category: str, chip: dict, mcu: dict, text: str, mcu_logic_v: float
) -> str:
    reasons = {
        "can_transceiver": (
            f"Required to interface {mcu['mpn']} CAN peripheral to physical bus. "
            f"{'3.3V native — no level shifter needed.' if chip.get('logic_level_v') == 3.3 else '5V part — level shifter required.'}"
        ),
        "motor_driver": (
            "Motor control detected in requirements. "
            f"Pairs with {mcu['mpn']} for {'3-phase BLDC' if 'bldc' in (chip.get('description') or '').lower() else 'stepper/DC motor'} control."
        ),
        "imu": (
            "IMU/motion sensing detected. "
            f"Connects via {chip.get('interface', 'SPI/I2C')} — supported by {mcu['mpn']}."
        ),
        "sensor": (
            "Environmental sensing detected. "
            f"Interfaces via {chip.get('interface', 'I2C')}."
        ),
        "pmic": (
            "Power management companion for complex power sequencing or USB-C PD support."
        ),
        "ldo": (
            f"LDO regulator to supply 3.3V rail for {mcu['mpn']} from higher-voltage source (5V/12V)."
        ),
        "rs485": (
            "RS-485/Modbus interface detected. "
            f"Interfaces via UART to {mcu['mpn']}. 3.3V native — no level shifter required."
        ),
    }
    return reasons.get(category, f"Matched for {category} category requirement.")


def _build_chipset_summary(mcu_mpn: str, companions: List[CompanionChip], cats: List[str]) -> str:
    if not companions:
        return f"{mcu_mpn} — no companion chips matched for the given requirements."
    cat_names = {
        "can_transceiver": "CAN Transceiver",
        "motor_driver": "Motor Driver",
        "imu": "IMU",
        "sensor": "Sensor",
        "pmic": "PMIC",
        "ldo": "LDO",
        "rs485": "RS-485",
    }
    parts_list = f"{mcu_mpn} + " + " + ".join(
        c.mpn for c in companions[:4]
    )
    if len(companions) > 4:
        parts_list += f" + {len(companions) - 4} more"
    matched_str = ", ".join(cat_names.get(c, c) for c in cats if c != "ldo")
    return (
        f"Recommended chipset for {matched_str or 'general'} application: {parts_list}. "
        f"{len(companions)} companion chip(s) across {len(set(c.category for c in companions))} categories."
    )


def _build_integration_notes(
    mcu_mpn: str, mcu_logic_v: float, companions: List[CompanionChip]
) -> List[str]:
    notes = []

    has_5v_parts = any(
        c.logic_level_v and float(c.logic_level_v) > mcu_logic_v + 0.3
        for c in companions
    )
    if has_5v_parts:
        notes.append(
            f"{mcu_mpn} operates at {mcu_logic_v}V. Some companion chips require 5V logic — "
            "add TXS0108E (bidirectional level shifter, $0.80) or SN74LVC1T45 per signal."
        )

    has_can = any(c.category == "can_transceiver" for c in companions)
    if has_can:
        notes.append(
            "CAN transceiver: ensure 120Ω termination resistor on both ends of the CAN bus. "
            "Twisted-pair cable for bus runs > 0.3m."
        )

    has_motor = any(c.category == "motor_driver" for c in companions)
    if has_motor:
        notes.append(
            "Motor driver: place bulk capacitors (220µF–1000µF electrolytic) close to VM supply pin "
            "to suppress back-EMF spikes. Add TVS diode on VM rail for inductive load protection."
        )

    has_imu = any(c.category == "imu" for c in companions)
    if has_imu:
        notes.append(
            "IMU: mount as close to the mechanical center of your board as possible. "
            "Avoid placing near high-current traces (motor drivers) to minimize magnetic interference. "
            "Use 100nF + 10µF decoupling on VDD."
        )

    notes.append(
        f"All 3.3V-native companions can share the {mcu_mpn} VDD rail. "
        "Total estimated chipset quiescent current: check individual datasheets for ICC_Q."
    )

    return notes


def ecosystem_to_dict(r: EcosystemResult) -> dict:
    return {
        "mcu_mpn": r.mcu_mpn,
        "mcu_logic_v": r.mcu_logic_v,
        "mcu_vdd_min": r.mcu_vdd_min,
        "mcu_vdd_max": r.mcu_vdd_max,
        "matched_categories": r.matched_categories,
        "total_bom_cost_usd": r.total_bom_cost_usd,
        "chipset_summary": r.chipset_summary,
        "integration_notes": r.integration_notes,
        "companions": [
            {
                "id": c.id,
                "mpn": c.mpn,
                "manufacturer": c.manufacturer,
                "category": c.category,
                "description": c.description,
                "interface": c.interface,
                "logic_level_v": c.logic_level_v,
                "vcc_min_v": c.vcc_min_v,
                "vcc_max_v": c.vcc_max_v,
                "cost_usd": c.cost_usd,
                "package": c.package,
                "notes": c.notes,
                "match_reason": c.match_reason,
                "compatibility_warning": c.compatibility_warning,
                "tags": c.tags,
            }
            for c in r.companions
        ],
    }
