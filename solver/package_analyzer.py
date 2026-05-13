"""
Package & PCB Manufacturing Cost Analyzer
==========================================
Analyzes the PCB complexity and manufacturing cost implications of a chosen
MCU package family. Injects actionable warnings into the design review.

Reference data based on:
  - IPC-7351 land pattern complexity
  - Typical PCB fab pricing (2-layer vs 4-layer vs HDI)
  - Placement machine pick-and-place minimum pitch
  - EMS (Electronics Manufacturing Services) complexity adders
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Package database: complexity and manufacturing requirements
# ---------------------------------------------------------------------------
_PACKAGE_DB: Dict[str, dict] = {
    "LQFP": {
        "full_name": "Low-Profile Quad Flat Package",
        "pcb_layers_min": 2,
        "requires_hdi": False,
        "min_pitch_mm": 0.4,
        "soldermask_side": "top",
        "hand_solderable": True,
        "reflow_profile": "standard",
        "cost_multiplier": 1.0,   # baseline
        "complexity": "Low",
        "inspection": "AOI sufficient",
        "notes": (
            "Industry-standard through-hole-compatible pads. "
            "Works on standard 2-layer PCB. Easiest to hand-solder for prototyping. "
            "AOI (Automated Optical Inspection) is fully sufficient."
        ),
        "warnings": [],
    },
    "UFQFPN": {
        "full_name": "Ultra-thin Fine-pitch Quad Flat No-lead Package",
        "pcb_layers_min": 2,
        "requires_hdi": False,
        "min_pitch_mm": 0.5,
        "soldermask_side": "top",
        "hand_solderable": False,
        "reflow_profile": "standard",
        "cost_multiplier": 1.1,
        "complexity": "Medium",
        "inspection": "AOI + X-ray recommended for thermal pad",
        "notes": (
            "QFN with exposed thermal pad on underside. Requires proper thermal pad via stitching. "
            "Cannot be hand-soldered. X-ray inspection recommended to verify thermal pad connection. "
            "Stencil design critical — paste volume controls."
        ),
        "warnings": [
            "Thermal pad requires via stitching to inner copper pour for heat dissipation.",
            "X-ray inspection recommended — thermal pad joint not visible to AOI.",
            "Cannot be hand-soldered in prototyping. Requires reflow oven or hot-air station.",
        ],
    },
    "TSSOP": {
        "full_name": "Thin Shrink Small Outline Package",
        "pcb_layers_min": 2,
        "requires_hdi": False,
        "min_pitch_mm": 0.65,
        "soldermask_side": "top",
        "hand_solderable": True,
        "reflow_profile": "standard",
        "cost_multiplier": 1.0,
        "complexity": "Low",
        "inspection": "AOI sufficient",
        "notes": "Similar to SOIC but narrower body. 0.65mm pitch — manageable with fine-tip iron.",
        "warnings": [],
    },
    "SOIC": {
        "full_name": "Small Outline Integrated Circuit",
        "pcb_layers_min": 2,
        "requires_hdi": False,
        "min_pitch_mm": 1.27,
        "soldermask_side": "top",
        "hand_solderable": True,
        "reflow_profile": "standard",
        "cost_multiplier": 0.95,
        "complexity": "Very Low",
        "inspection": "Visual sufficient",
        "notes": "Largest-pitch SMD package. Very easy to hand-solder and inspect. Lowest risk.",
        "warnings": [],
    },
    "BGA": {
        "full_name": "Ball Grid Array",
        "pcb_layers_min": 4,
        "requires_hdi": False,
        "min_pitch_mm": 0.8,
        "soldermask_side": "both",
        "hand_solderable": False,
        "reflow_profile": "standard",
        "cost_multiplier": 1.6,
        "complexity": "High",
        "inspection": "X-ray mandatory",
        "notes": (
            "All solder joints are hidden under the package. "
            "Minimum 4-layer PCB required for fan-out routing. "
            "X-ray inspection is mandatory — AOI cannot inspect BGA joints. "
            "Rework is difficult and requires specialist BGA rework station."
        ),
        "warnings": [
            "⚠️ X-ray inspection mandatory — no joints visible post-reflow.",
            "⚠️ Minimum 4-layer PCB required for signal fan-out.",
            "⚠️ Rework requires specialist BGA rework station (~$5k–$30k equipment).",
            "⚠️ PCB bare-board cost increases ~40–60% vs LQFP equivalent.",
            "BGA assembly NRE (stencil, programming) adds to prototype cost.",
        ],
    },
    "TFBGA": {
        "full_name": "Thin Fine-pitch Ball Grid Array",
        "pcb_layers_min": 4,
        "requires_hdi": False,
        "min_pitch_mm": 0.5,
        "soldermask_side": "both",
        "hand_solderable": False,
        "reflow_profile": "standard",
        "cost_multiplier": 1.8,
        "complexity": "High",
        "inspection": "X-ray mandatory",
        "notes": (
            "Fine-pitch BGA (0.5mm) — more challenging fan-out than standard BGA. "
            "Still manageable without HDI if via diameter constraints are met. "
            "Requires 4-layer minimum with 0.1mm drill capability."
        ),
        "warnings": [
            "⚠️ 0.5mm pitch — requires tight PCB design rules (≤0.1mm drill).",
            "⚠️ X-ray inspection mandatory.",
            "⚠️ 4-layer PCB minimum. Consider HDI for dense designs.",
        ],
    },
    "WLCSP": {
        "full_name": "Wafer-Level Chip Scale Package",
        "pcb_layers_min": 4,
        "requires_hdi": True,
        "min_pitch_mm": 0.4,
        "soldermask_side": "both",
        "hand_solderable": False,
        "reflow_profile": "lead-free-ramp",
        "cost_multiplier": 2.4,
        "complexity": "Very High",
        "inspection": "X-ray + acoustic microscopy",
        "notes": (
            "Die-size package — smallest possible footprint. "
            "REQUIRES HDI (High-Density Interconnect) PCB with blind/buried vias. "
            "HDI PCBs are 2–4× more expensive than standard PCBs. "
            "Only suitable for volume production where size is critical (wearables, hearables). "
            "Not recommended for prototyping or low-volume designs."
        ),
        "warnings": [
            "⚠️ REQUIRES HDI PCB — blind/buried vias mandatory. Board cost +100–200% vs LQFP.",
            "⚠️ X-ray + acoustic microscopy inspection required.",
            "⚠️ No hand-soldering possible under any circumstances.",
            "⚠️ Not recommended for prototyping. Consider UFQFPN variant for development.",
            "⚠️ Moisture sensitivity level (MSL) handling required — bake before use.",
            "⚠️ Minimum PCB trace/space: 75µm/75µm — specialized fabrication required.",
        ],
    },
    "UFBGA": {
        "full_name": "Ultra Fine-pitch Ball Grid Array",
        "pcb_layers_min": 6,
        "requires_hdi": True,
        "min_pitch_mm": 0.4,
        "soldermask_side": "both",
        "hand_solderable": False,
        "reflow_profile": "lead-free-ramp",
        "cost_multiplier": 2.8,
        "complexity": "Very High",
        "inspection": "X-ray + acoustic microscopy",
        "notes": (
            "Ultra-fine-pitch BGA requiring HDI PCB with sequential lamination. "
            "Typically used in smartphones and high-density embedded designs. "
            "6-layer minimum PCB. Strictly volume-production only."
        ),
        "warnings": [
            "⚠️ REQUIRES HDI PCB with sequential lamination (6+ layers).",
            "⚠️ Board fabrication cost +200–350% vs standard LQFP design.",
            "⚠️ Prototype assembly by specialized EMS only.",
        ],
    },
    "VQFN": {
        "full_name": "Very thin Quad Flat No-lead",
        "pcb_layers_min": 2,
        "requires_hdi": False,
        "min_pitch_mm": 0.5,
        "soldermask_side": "top",
        "hand_solderable": False,
        "reflow_profile": "standard",
        "cost_multiplier": 1.1,
        "complexity": "Medium",
        "inspection": "AOI + X-ray recommended",
        "notes": "Similar to UFQFPN but taller body. Standard reflow, thermal pad via-stitching required.",
        "warnings": [
            "Thermal pad via stitching required.",
            "X-ray recommended to inspect thermal pad connection.",
        ],
    },
    "SO": {
        "full_name": "Small Outline",
        "pcb_layers_min": 2,
        "requires_hdi": False,
        "min_pitch_mm": 1.27,
        "soldermask_side": "top",
        "hand_solderable": True,
        "reflow_profile": "standard",
        "cost_multiplier": 0.95,
        "complexity": "Very Low",
        "inspection": "Visual sufficient",
        "notes": "Wide-body SO package. Very easy to work with. Used mostly for smaller STM32 variants.",
        "warnings": [],
    },
}

# Generic fallback for unknown packages
_DEFAULT_PACKAGE = {
    "full_name": "Unknown Package",
    "pcb_layers_min": 2,
    "requires_hdi": False,
    "min_pitch_mm": None,
    "hand_solderable": None,
    "reflow_profile": "standard",
    "cost_multiplier": 1.0,
    "complexity": "Unknown",
    "inspection": "Refer to package spec",
    "notes": "Package information not available in our database.",
    "warnings": [],
}


@dataclass
class PackageAnalysis:
    """Full package analysis result."""
    mpn: str
    package_family: str
    package_full_name: str
    pin_count: Optional[int]

    pcb_layers_min: int
    requires_hdi: bool
    min_pitch_mm: Optional[float]
    hand_solderable: Optional[bool]
    reflow_profile: str
    cost_multiplier: float
    complexity: str
    inspection_method: str
    description: str
    warnings: List[str]
    cost_estimate_notes: str
    design_recommendations: List[str]


class PackageAnalyzer:
    """
    Analyzes PCB manufacturing complexity for a given part's package.
    Can also compare two parts' packages for rework assessment.
    """

    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool

    async def analyze(self, part_id: str) -> PackageAnalysis:
        uuid_id = UUID(part_id)

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT p.mpn, p.package_family, p.package_name, p.pin_count,
                       ms.flash_kb, ms.max_mhz, ms.has_fpu, ms.vdd_min_v, ms.vdd_max_v
                FROM parts p
                LEFT JOIN mcu_specs ms ON ms.part_id = p.id
                WHERE p.id = $1
            """, uuid_id)

        if not row:
            raise ValueError(f"Part {part_id} not found")

        data = dict(row)
        mpn = data["mpn"]
        pkg_family = (data.get("package_family") or "").upper()
        pkg_name = (data.get("package_name") or "").upper()
        pin_count = data.get("pin_count")

        # Resolve package info — try exact family match
        pkg_info = _PACKAGE_DB.get(pkg_family, None)
        if pkg_info is None:
            # Try partial match
            for key in _PACKAGE_DB:
                if key in pkg_family or pkg_family in key:
                    pkg_info = _PACKAGE_DB[key]
                    break
        if pkg_info is None:
            pkg_info = _DEFAULT_PACKAGE

        # Build cost estimate notes
        base_multiplier = pkg_info["cost_multiplier"]
        cost_notes = _build_cost_notes(pkg_family, pkg_info, pin_count)

        # Build design recommendations
        design_recs = _build_design_recs(pkg_family, pkg_info, data)

        return PackageAnalysis(
            mpn=mpn,
            package_family=pkg_family,
            package_full_name=pkg_info["full_name"],
            pin_count=pin_count,
            pcb_layers_min=pkg_info["pcb_layers_min"],
            requires_hdi=pkg_info["requires_hdi"],
            min_pitch_mm=pkg_info.get("min_pitch_mm"),
            hand_solderable=pkg_info.get("hand_solderable"),
            reflow_profile=pkg_info["reflow_profile"],
            cost_multiplier=base_multiplier,
            complexity=pkg_info["complexity"],
            inspection_method=pkg_info["inspection"],
            description=pkg_info["notes"],
            warnings=list(pkg_info["warnings"]),
            cost_estimate_notes=cost_notes,
            design_recommendations=design_recs,
        )


def _build_cost_notes(pkg_family: str, info: dict, pin_count: Optional[int]) -> str:
    mult = info["cost_multiplier"]
    layers = info["pcb_layers_min"]
    hdi = info["requires_hdi"]

    if pkg_family == "LQFP":
        return (
            "LQFP is the baseline package — most cost-effective for PCB manufacturing. "
            f"Standard 2-layer PCB, AOI inspection. Relative manufacturing index: 1.0×."
        )

    pct = int((mult - 1.0) * 100)
    direction = "more expensive" if pct >= 0 else "cheaper"
    note = f"Estimated {abs(pct)}% {direction} to manufacture than equivalent LQFP design. "
    note += f"Minimum {layers}-layer PCB required. "

    if hdi:
        note += (
            "HDI PCB required — typical bare-board cost is 2–4× standard PCB. "
            "Assembly costs also increase due to specialist equipment and inspection requirements."
        )
    elif layers > 2:
        note += (
            f"{layers}-layer PCB adds approximately 40–80% to bare-board cost vs 2-layer. "
            "Fan-out routing complexity is the main driver."
        )

    return note


def _build_design_recs(pkg_family: str, info: dict, part_data: dict) -> List[str]:
    recs = []

    if pkg_family == "WLCSP" or pkg_family == "UFBGA":
        recs.append(
            "For prototyping/development, use the LQFP or UFQFPN variant of the same MCU family. "
            "Switch to WLCSP/UFBGA only for final production where PCB area is critical."
        )

    if pkg_family in ("BGA", "TFBGA", "UFBGA", "WLCSP"):
        recs.append(
            "Design PCB with controlled-impedance traces for high-speed signals. "
            "Place decoupling capacitors as close to VDD balls as possible (within 0.5mm)."
        )
        recs.append(
            "Use a via-in-pad design (filled and planarized) for BGA/WLCSP to minimize inductance."
        )

    if pkg_family in ("UFQFPN", "VQFN"):
        recs.append(
            "Design thermal pad with cross-hatch copper pour and via stitching to inner ground plane. "
            "Minimum 9 thermal vias (3×3 grid) of 0.3mm drill diameter."
        )
        recs.append(
            "Set stencil aperture to 60–70% of exposed pad area to prevent bridging during reflow."
        )

    if not info.get("hand_solderable"):
        recs.append(
            "This package cannot be hand-soldered. Ensure your prototyping setup includes "
            "a reflow oven (or at minimum a hot-air rework station) before PCB assembly."
        )

    if pkg_family == "LQFP":
        pin_count = part_data.get("pin_count")
        if pin_count and pin_count >= 100:
            recs.append(
                f"LQFP-{pin_count} with many pins: use 0.4mm pitch variant if available. "
                "Ensure your PCB fab supports ≥0.18mm solder mask web between pads."
            )
        else:
            recs.append(
                "✅ LQFP is the optimal choice for development and low-volume production. "
                "No special PCB requirements. Standard assembly services suffice."
            )

    return recs


def analysis_to_dict(a: PackageAnalysis) -> dict:
    return {
        "mpn": a.mpn,
        "package_family": a.package_family,
        "package_full_name": a.package_full_name,
        "pin_count": a.pin_count,
        "pcb_layers_min": a.pcb_layers_min,
        "requires_hdi": a.requires_hdi,
        "min_pitch_mm": a.min_pitch_mm,
        "hand_solderable": a.hand_solderable,
        "reflow_profile": a.reflow_profile,
        "cost_multiplier": a.cost_multiplier,
        "complexity": a.complexity,
        "inspection_method": a.inspection_method,
        "description": a.description,
        "warnings": a.warnings,
        "cost_estimate_notes": a.cost_estimate_notes,
        "design_recommendations": a.design_recommendations,
    }
