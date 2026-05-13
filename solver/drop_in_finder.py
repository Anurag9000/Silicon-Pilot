"""
Drop-In Replacement Engine
==========================
Given an existing MCU part, finds the best drop-in replacements ranked by
how little schematic and firmware rework is required.

Scoring is built on four independent compatibility axes:
  1. Package compatibility     — same family/pin count = zero rework
  2. Core compatibility        — same ARM core = minimal firmware changes
  3. Peripheral compatibility  — same peripheral set = no driver changes
  4. Voltage compatibility     — same VDD range = no power-rail changes

Each axis returns a 0–1 score; the weighted total determines the overall
"rework level" category:

  ≥ 0.90  → Drop-in (swap without schematic changes)
  ≥ 0.70  → Minor (footprint change or minor pin-remap, same board layer)
  ≥ 0.50  → Moderate (some peripheral driver updates, possible layout change)
  < 0.50  → Major (significant re-design required)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)

# Weight of each compatibility axis in the composite score
_WEIGHTS = {
    "package":    0.35,
    "core":       0.25,
    "peripheral": 0.25,
    "voltage":    0.15,
}

_REWORK_LABELS = {
    (0.90, 1.01): "Drop-In",
    (0.70, 0.90): "Minor",
    (0.50, 0.70): "Moderate",
    (0.00, 0.50): "Major",
}

_CORE_COMPAT = {
    # Within the same core family = fully compatible
    "Cortex-M0":  {"Cortex-M0", "Cortex-M0+"},
    "Cortex-M0+": {"Cortex-M0", "Cortex-M0+"},
    "Cortex-M3":  {"Cortex-M3"},
    "Cortex-M4":  {"Cortex-M4", "Cortex-M4F"},
    "Cortex-M4F": {"Cortex-M4", "Cortex-M4F"},
    "Cortex-M7":  {"Cortex-M7", "Cortex-M7F"},
    "Cortex-M7F": {"Cortex-M7", "Cortex-M7F"},
    "Cortex-M33": {"Cortex-M33"},
}


@dataclass
class DropInCandidate:
    """A single drop-in replacement candidate with full scoring breakdown."""
    part_id: str
    mpn: str
    manufacturer: str
    family: str
    package_family: str
    pin_count: Optional[int]
    flash_kb: Optional[int]
    sram_kb: Optional[int]
    max_mhz: Optional[int]
    core: Optional[str]
    vdd_min_v: Optional[float]
    vdd_max_v: Optional[float]
    cost_usd: Optional[float]
    # Scores
    package_score: float
    core_score: float
    peripheral_score: float
    voltage_score: float
    composite_score: float
    rework_level: str
    rework_notes: List[str]


def _rework_label(score: float) -> str:
    for (lo, hi), label in _REWORK_LABELS.items():
        if lo <= score < hi:
            return label
    return "Major"


def _package_score(source: dict, cand: dict) -> float:
    """
    Score package compatibility.
    Same family + same pin count = 1.0
    Same family, different pin count = 0.7
    Different family, same pin count = 0.5
    Completely different = 0.1
    """
    src_fam = (source.get("package_family") or "").upper()
    cnd_fam = (cand.get("package_family") or "").upper()
    src_pins = source.get("pin_count")
    cnd_pins = cand.get("pin_count")

    same_family = src_fam == cnd_fam and src_fam != ""
    same_pins = (src_pins is not None and cnd_pins is not None and src_pins == cnd_pins)

    if same_family and same_pins:
        return 1.0
    if same_family:
        return 0.70
    if same_pins:
        return 0.50
    return 0.10


def _core_score(source: dict, cand: dict) -> float:
    """Score ARM core compatibility (firmware effort)."""
    src_core = (source.get("core") or "").strip()
    cnd_core = (cand.get("core") or "").strip()

    if src_core == cnd_core:
        return 1.0

    # Check cross-core compatibility table
    compat_set = _CORE_COMPAT.get(src_core, {src_core})
    if cnd_core in compat_set:
        return 0.90

    # Upgrade within the Cortex-M family (M3→M4 is mostly compatible)
    src_level = _core_level(src_core)
    cnd_level = _core_level(cnd_core)
    if src_level > 0 and cnd_level > 0:
        diff = abs(src_level - cnd_level)
        return max(0.30, 1.0 - diff * 0.35)
    return 0.30


def _core_level(core: str) -> int:
    """Convert core name to numeric level for comparison."""
    c = core.upper()
    if "M0+" in c:  return 1
    if "M0"  in c:  return 1
    if "M3"  in c:  return 3
    if "M4"  in c:  return 4
    if "M7"  in c:  return 7
    if "M33" in c:  return 33
    return 0


def _peripheral_score(source: dict, cand: dict) -> float:
    """
    Score peripheral compatibility.
    For each peripheral count, penalize if candidate has fewer than source.
    Bonus if candidate has more (superset = easy to port).
    """
    peripherals = [
        ("uart_count", 0.20),
        ("spi_count",  0.15),
        ("i2c_count",  0.15),
        ("can_count",  0.15),
        ("can_fd_count", 0.10),
        ("adc_channels", 0.10),
        ("usb_fs",     0.10),
        ("ethernet",   0.05),
    ]

    total_weight = sum(w for _, w in peripherals)
    score = 0.0

    for field, weight in peripherals:
        src_val = source.get(field) or 0
        cnd_val = cand.get(field) or 0

        if src_val == 0:
            # Source doesn't need this peripheral → candidate having it is neutral
            score += weight
        elif cnd_val >= src_val:
            # Candidate has at least as many → compatible
            score += weight
        else:
            # Candidate has fewer → penalize proportionally
            ratio = cnd_val / src_val if src_val > 0 else 0
            score += weight * ratio

    return score / total_weight


def _voltage_score(source: dict, cand: dict) -> float:
    """Score VDD range compatibility."""
    src_min = source.get("vdd_min_v") or source.get("voltage_min_v")
    src_max = source.get("vdd_max_v") or source.get("voltage_max_v")
    cnd_min = cand.get("vdd_min_v") or cand.get("voltage_min_v")
    cnd_max = cand.get("vdd_max_v") or cand.get("voltage_max_v")

    if src_min is None or cnd_min is None:
        return 0.75  # No data → assume compatible

    try:
        src_min, src_max = float(src_min), float(src_max)
        cnd_min, cnd_max = float(cnd_min), float(cnd_max)
    except (TypeError, ValueError):
        return 0.75

    # Check if candidate range covers source range
    covers = cnd_min <= src_min and cnd_max >= src_max
    if covers:
        return 1.0

    # Partial overlap
    overlap_lo = max(src_min, cnd_min)
    overlap_hi = min(src_max, cnd_max)
    if overlap_hi <= overlap_lo:
        return 0.0  # No overlap — incompatible rails

    src_range = src_max - src_min or 0.001
    overlap = (overlap_hi - overlap_lo) / src_range
    return round(overlap, 3)


def _build_notes(source: dict, cand: dict, scores: dict) -> List[str]:
    """Build a list of human-readable rework notes."""
    notes = []

    # Package notes
    src_fam = (source.get("package_family") or "?").upper()
    cnd_fam = (cand.get("package_family") or "?").upper()
    src_pins = source.get("pin_count")
    cnd_pins = cand.get("pin_count")

    if src_fam != cnd_fam:
        notes.append(f"Package family change: {src_fam} → {cnd_fam}. New footprint required on PCB.")
    elif src_pins and cnd_pins and src_pins != cnd_pins:
        delta = cnd_pins - src_pins
        notes.append(f"Pin count change: {src_pins} → {cnd_pins} pins ({delta:+d}). "
                     f"{'Expanded pinout — verify power/GND distribution.' if delta > 0 else 'Reduced pinout — verify all signals fit.'}")
    else:
        notes.append("✅ Same package family and pin count — physical drop-in replacement.")

    # Core notes
    src_core = source.get("core") or "?"
    cnd_core = cand.get("core") or "?"
    if src_core != cnd_core:
        notes.append(f"Core change: {src_core} → {cnd_core}. "
                     f"Recompile with matching FPU/DSP flags. "
                     f"{'FPU available on candidate.' if 'F' in cnd_core else 'No FPU on candidate — check floating-point code.'}")
    else:
        notes.append(f"✅ Same {src_core} core — binary/HAL compatible.")

    # Flash/RAM notes
    src_flash = source.get("flash_kb") or 0
    cnd_flash = cand.get("flash_kb") or 0
    src_ram = source.get("sram_kb") or source.get("ram_kb") or 0
    cnd_ram = cand.get("sram_kb") or cand.get("ram_kb") or 0

    if cnd_flash < src_flash:
        notes.append(f"⚠️ Flash reduced: {src_flash}KB → {cnd_flash}KB. May need code-size optimisation.")
    if cnd_ram < src_ram:
        notes.append(f"⚠️ SRAM reduced: {src_ram}KB → {cnd_ram}KB. Review stack/heap sizes.")

    # Peripheral notes
    for peri, label in [("can_count","CAN"), ("can_fd_count","CAN-FD"), ("uart_count","UART"),
                         ("spi_count","SPI"), ("usb_fs","USB-FS"), ("ethernet","Ethernet")]:
        src_v = source.get(peri) or 0
        cnd_v = cand.get(peri) or 0
        if src_v > 0 and cnd_v < src_v:
            notes.append(f"⚠️ {label} count reduced: {src_v} → {cnd_v}. May need external peripheral expander.")

    # Voltage notes
    if scores["voltage"] < 0.9:
        notes.append(f"⚠️ VDD range mismatch. Verify power rail compatibility before swapping.")

    return notes


class DropInFinder:
    """
    Finds drop-in replacements for a given MCU part.

    Usage:
        finder = DropInFinder(db_pool)
        results = await finder.find(part_id, max_results=8)
    """

    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool

    async def find(self, part_id: str, max_results: int = 8) -> dict:
        """
        Find drop-in replacements for a given part_id.

        Returns a structured dict with:
          - source: the original part info
          - replacements: ranked list of DropInCandidate
          - summary: human-readable summary
        """
        try:
            uuid_id = UUID(part_id)
        except ValueError:
            raise ValueError(f"Invalid UUID: {part_id}")

        async with self.pool.acquire() as conn:
            # Load source part
            source_row = await conn.fetchrow("""
                SELECT p.id, p.mpn, p.manufacturer, p.family,
                       p.package_family, p.pin_count,
                       ms.core, ms.flash_kb, ms.sram_kb, ms.ram_kb, ms.max_mhz,
                       ms.uart_count, ms.spi_count, ms.i2c_count,
                       ms.can_count, ms.can_fd_count, ms.usb_fs, ms.ethernet,
                       ms.adc_channels, ms.has_fpu,
                       ms.vdd_min_v, ms.vdd_max_v,
                       ms.voltage_min_v, ms.voltage_max_v,
                       ms.cost_usd
                FROM parts p
                JOIN mcu_specs ms ON ms.part_id = p.id
                WHERE p.id = $1
            """, uuid_id)

            if not source_row:
                raise ValueError(f"Part {part_id} not found or has no spec data")

            source = dict(source_row)

            # Load all other parts with compatible flash range (within 4x)
            # to avoid comparing STM32F4 with 1MB against STM32C0 with 8KB
            src_flash = source.get("flash_kb") or 64
            flash_min = src_flash // 4
            flash_max = src_flash * 8

            candidate_rows = await conn.fetch("""
                SELECT p.id, p.mpn, p.manufacturer, p.family,
                       p.package_family, p.pin_count,
                       ms.core, ms.flash_kb, ms.sram_kb, ms.ram_kb, ms.max_mhz,
                       ms.uart_count, ms.spi_count, ms.i2c_count,
                       ms.can_count, ms.can_fd_count, ms.usb_fs, ms.ethernet,
                       ms.adc_channels, ms.has_fpu,
                       ms.vdd_min_v, ms.vdd_max_v,
                       ms.voltage_min_v, ms.voltage_max_v,
                       ms.cost_usd
                FROM parts p
                JOIN mcu_specs ms ON ms.part_id = p.id
                WHERE p.id != $1
                  AND ms.flash_kb BETWEEN $2 AND $3
                  AND p.status = 'active'
                ORDER BY p.manufacturer, p.family, p.mpn
            """, uuid_id, flash_min, flash_max)

        # Score all candidates
        candidates: List[DropInCandidate] = []

        for row in candidate_rows:
            cand = dict(row)
            scores = {
                "package":    _package_score(source, cand),
                "core":       _core_score(source, cand),
                "peripheral": _peripheral_score(source, cand),
                "voltage":    _voltage_score(source, cand),
            }
            composite = sum(scores[k] * _WEIGHTS[k] for k in _WEIGHTS)
            notes = _build_notes(source, cand, scores)

            candidates.append(DropInCandidate(
                part_id=str(cand["id"]),
                mpn=cand["mpn"],
                manufacturer=cand["manufacturer"],
                family=cand.get("family") or "",
                package_family=cand.get("package_family") or "",
                pin_count=cand.get("pin_count"),
                flash_kb=cand.get("flash_kb"),
                sram_kb=cand.get("sram_kb") or cand.get("ram_kb"),
                max_mhz=cand.get("max_mhz"),
                core=cand.get("core"),
                vdd_min_v=float(cand["vdd_min_v"]) if cand.get("vdd_min_v") else None,
                vdd_max_v=float(cand["vdd_max_v"]) if cand.get("vdd_max_v") else None,
                cost_usd=float(cand["cost_usd"]) if cand.get("cost_usd") else None,
                package_score=round(scores["package"], 3),
                core_score=round(scores["core"], 3),
                peripheral_score=round(scores["peripheral"], 3),
                voltage_score=round(scores["voltage"], 3),
                composite_score=round(composite, 3),
                rework_level=_rework_label(composite),
                rework_notes=notes,
            ))

        # Sort by composite score descending
        candidates.sort(key=lambda c: c.composite_score, reverse=True)
        top = candidates[:max_results]

        # Count by rework level
        level_counts = {"Drop-In": 0, "Minor": 0, "Moderate": 0, "Major": 0}
        for c in candidates:
            level_counts[c.rework_level] = level_counts.get(c.rework_level, 0) + 1

        return {
            "source_part": {
                "id": str(source["id"]),
                "mpn": source["mpn"],
                "manufacturer": source["manufacturer"],
                "family": source.get("family"),
                "package_family": source.get("package_family"),
                "pin_count": source.get("pin_count"),
                "flash_kb": source.get("flash_kb"),
                "sram_kb": source.get("sram_kb") or source.get("ram_kb"),
                "max_mhz": source.get("max_mhz"),
                "core": source.get("core"),
            },
            "replacements": [
                {
                    "part_id": c.part_id,
                    "mpn": c.mpn,
                    "manufacturer": c.manufacturer,
                    "family": c.family,
                    "package_family": c.package_family,
                    "pin_count": c.pin_count,
                    "flash_kb": c.flash_kb,
                    "sram_kb": c.sram_kb,
                    "max_mhz": c.max_mhz,
                    "core": c.core,
                    "vdd_min_v": c.vdd_min_v,
                    "vdd_max_v": c.vdd_max_v,
                    "cost_usd": c.cost_usd,
                    "scores": {
                        "package": c.package_score,
                        "core": c.core_score,
                        "peripheral": c.peripheral_score,
                        "voltage": c.voltage_score,
                        "composite": c.composite_score,
                    },
                    "rework_level": c.rework_level,
                    "rework_notes": c.rework_notes,
                }
                for c in top
            ],
            "total_candidates_searched": len(candidates),
            "rework_level_counts": level_counts,
            "summary": (
                f"Found {level_counts['Drop-In']} drop-in, {level_counts['Minor']} minor-rework, "
                f"{level_counts['Moderate']} moderate replacements for {source['mpn']} "
                f"from {len(candidates)} candidates in the same flash class."
            ),
        }
