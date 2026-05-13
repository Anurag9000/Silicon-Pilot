"""
Advanced Power Profiler & Battery Life Estimator
=================================================
Calculates realistic battery life using:
  - Real datasheet power values seeded from mcu_specs (active_ma, standby_ua, sleep_ua)
  - User-defined duty cycle (run%, sleep%, stop%)
  - Peripheral active current contributions
  - External component overhead
  - Battery chemistry derating

All intermediate math is exposed so the UI can render a full breakdown.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Typical STM32 peripheral current draws (µA) when active at 3.3V
# Source: ST application notes AN4488, AN5096
# ---------------------------------------------------------------------------
_PERIPHERAL_CURRENT_UA: Dict[str, float] = {
    "uart":     180.0,
    "usart":    180.0,
    "spi":      300.0,
    "i2c":      150.0,
    "can":      650.0,
    "can_fd":   800.0,
    "adc":      600.0,   # per conversion burst
    "dac":      400.0,
    "timer":     80.0,
    "pwm":       80.0,
    "usb":     3500.0,   # USB FS active
    "ethernet": 8000.0,  # Ethernet PHY + MAC
    "rng":      100.0,
    "dma":       50.0,
}

# Battery usable capacity derating factors
_BATTERY_DERATING: Dict[str, float] = {
    "Li-Ion":  0.85,
    "Li-Po":   0.85,
    "LiPo":    0.85,
    "Alkaline": 0.65,
    "NiMH":    0.75,
    "LiFePO4": 0.90,
    "Coin":    0.70,
}

# Peukert correction: high current discharge reduces effective capacity
def _peukert_factor(avg_current_ma: float) -> float:
    """Simple linear Peukert correction (n≈1.1 for Li-Ion)."""
    if avg_current_ma < 1.0:
        return 1.05   # sub-mA draw — slight benefit
    if avg_current_ma < 50:
        return 1.0
    if avg_current_ma < 200:
        return 0.95
    return 0.90


@dataclass
class PowerMode:
    name: str           # "run" | "sleep" | "stop" | "standby"
    percent: float      # 0–100 percentage of time in this mode
    freq_mhz: Optional[float] = None  # only for run mode


@dataclass
class ExternalLoad:
    name: str
    current_ma: float
    duty_percent: float = 100.0  # percentage of time this load is active


@dataclass
class PowerBreakdown:
    mode: str
    current_ua: float
    time_percent: float
    weighted_ua: float   # current_ua * time_percent / 100


@dataclass
class PowerProfile:
    """Complete power analysis result."""
    mpn: str
    core: Optional[str]
    system_voltage_v: float

    # Per-mode breakdown
    mode_breakdown: List[PowerBreakdown]

    # Peripheral contributions
    peripheral_breakdown: Dict[str, float]   # name → average µA

    # External load contributions
    external_breakdown: Dict[str, float]

    # Totals
    mcu_avg_ua: float          # weighted average MCU current in µA
    peripheral_avg_ua: float
    external_avg_ua: float
    total_avg_ua: float
    total_avg_ma: float

    # Battery results
    battery_capacity_mah: Optional[float]
    battery_chemistry: str
    usable_capacity_mah: Optional[float]
    lifetime_hours: Optional[float]
    lifetime_days: Optional[float]

    # Optimization tips
    recommendations: List[str]

    # Data quality flag
    using_estimated_values: bool


class PowerProfiler:
    """
    Computes a detailed power profile for a given MCU + duty cycle.

    Usage:
        profiler = PowerProfiler(db_pool)
        result = await profiler.compute(
            part_id="<uuid>",
            modes=[{"name":"run","percent":10,"freq_mhz":80},
                   {"name":"stop","percent":90}],
            peripherals=[{"type":"can","duty_percent":80},
                         {"type":"uart","duty_percent":30}],
            external_loads=[{"name":"CAN Transceiver","current_ma":0.07,"duty_percent":80}],
            battery_mah=2000,
            battery_chemistry="Li-Po",
        )
    """

    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool

    async def compute(
        self,
        part_id: str,
        modes: List[Dict],
        peripherals: List[Dict],
        external_loads: List[Dict],
        battery_mah: Optional[float] = None,
        battery_chemistry: str = "Li-Po",
        system_voltage_v: float = 3.3,
    ) -> PowerProfile:

        uuid_id = UUID(part_id)

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT p.mpn, p.family,
                       ms.core, ms.max_mhz,
                       ms.active_ma, ms.standby_ua, ms.sleep_ua,
                       ms.vdd_min_v, ms.vdd_max_v
                FROM parts p
                JOIN mcu_specs ms ON ms.part_id = p.id
                WHERE p.id = $1
            """, uuid_id)

        if not row:
            raise ValueError(f"Part {part_id} not found or missing mcu_specs data")

        data = dict(row)
        mpn = data["mpn"]
        core = data.get("core")

        # ── Pull power figures from DB ──────────────────────────────────────
        # active_ma is in milliamps; convert to µA for uniform math
        db_run_ua = float(data["active_ma"]) * 1000.0 if data.get("active_ma") else None
        db_sleep_ua = float(data["sleep_ua"]) if data.get("sleep_ua") else None
        db_standby_ua = float(data["standby_ua"]) if data.get("standby_ua") else None
        max_mhz = data.get("max_mhz") or 100

        using_estimated = db_run_ua is None

        # Fallback estimates (typical for Cortex-M4 @ 3.3V)
        if db_run_ua is None:
            db_run_ua = 20_000.0      # 20mA typical run
        if db_sleep_ua is None:
            db_sleep_ua = 500.0       # 500µA sleep
        if db_standby_ua is None:
            db_standby_ua = 2.0       # 2µA standby

        # ── Validate & normalise mode percentages ───────────────────────────
        total_pct = sum(m.get("percent", 0) for m in modes)
        if abs(total_pct - 100.0) > 0.5:
            # Scale to 100% if user gave rough numbers
            for m in modes:
                m["percent"] = m.get("percent", 0) * 100.0 / max(total_pct, 0.01)

        # ── Compute per-mode current ─────────────────────────────────────────
        mode_breakdown: List[PowerBreakdown] = []
        mcu_avg_ua = 0.0

        for m in modes:
            name = m.get("name", "run").lower()
            pct  = float(m.get("percent", 0))
            freq = float(m.get("freq_mhz", max_mhz) or max_mhz)

            if name in ("run", "active"):
                # Scale run current linearly by frequency ratio
                freq_ratio = min(freq / max(max_mhz, 1), 1.0)
                mode_ua = db_run_ua * freq_ratio
                # Add leakage floor (chip never goes to 0 even at 1MHz)
                mode_ua = max(mode_ua, db_run_ua * 0.05)
            elif name == "sleep":
                mode_ua = db_sleep_ua
            elif name in ("stop", "stop1", "stop2"):
                # Stop mode ≈ 10–50x better than sleep
                mode_ua = db_sleep_ua * 0.08
            elif name in ("standby", "shutdown"):
                mode_ua = db_standby_ua
            else:
                mode_ua = db_run_ua  # unknown → assume run

            weighted = mode_ua * pct / 100.0
            mcu_avg_ua += weighted

            mode_breakdown.append(PowerBreakdown(
                mode=name,
                current_ua=round(mode_ua, 2),
                time_percent=round(pct, 1),
                weighted_ua=round(weighted, 2),
            ))

        # ── Peripheral contributions ─────────────────────────────────────────
        peripheral_breakdown: Dict[str, float] = {}
        peripheral_avg_ua = 0.0

        for p in peripherals:
            ptype = (p.get("type") or p.get("peripheral_type") or "").lower()
            duty  = float(p.get("duty_percent", 100)) / 100.0
            base_ua = _PERIPHERAL_CURRENT_UA.get(ptype, 200.0)
            avg_ua = base_ua * duty
            peripheral_breakdown[ptype] = round(avg_ua, 2)
            peripheral_avg_ua += avg_ua

        # ── External loads ───────────────────────────────────────────────────
        external_breakdown: Dict[str, float] = {}
        external_avg_ua = 0.0

        for ext in external_loads:
            name = ext.get("name", "external")
            current_ma = float(ext.get("current_ma", 0))
            duty = float(ext.get("duty_percent", 100)) / 100.0
            avg_ua = current_ma * 1000.0 * duty
            external_breakdown[name] = round(avg_ua, 2)
            external_avg_ua += avg_ua

        # ── Totals ───────────────────────────────────────────────────────────
        total_avg_ua = mcu_avg_ua + peripheral_avg_ua + external_avg_ua
        total_avg_ma = total_avg_ua / 1000.0

        # ── Battery life ─────────────────────────────────────────────────────
        lifetime_hours = None
        lifetime_days = None
        usable_mah = None

        if battery_mah and total_avg_ma > 0:
            derating = _BATTERY_DERATING.get(battery_chemistry, 0.80)
            peukert = _peukert_factor(total_avg_ma)
            usable_mah = battery_mah * derating * peukert
            lifetime_hours = usable_mah / total_avg_ma
            lifetime_days = lifetime_hours / 24.0

        # ── Recommendations ──────────────────────────────────────────────────
        recommendations = _build_recommendations(
            mcu_avg_ua, peripheral_avg_ua, external_avg_ua,
            total_avg_ma, lifetime_days, mode_breakdown, peripherals,
        )

        return PowerProfile(
            mpn=mpn,
            core=core,
            system_voltage_v=system_voltage_v,
            mode_breakdown=mode_breakdown,
            peripheral_breakdown=peripheral_breakdown,
            external_breakdown=external_breakdown,
            mcu_avg_ua=round(mcu_avg_ua, 2),
            peripheral_avg_ua=round(peripheral_avg_ua, 2),
            external_avg_ua=round(external_avg_ua, 2),
            total_avg_ua=round(total_avg_ua, 2),
            total_avg_ma=round(total_avg_ma, 4),
            battery_capacity_mah=battery_mah,
            battery_chemistry=battery_chemistry,
            usable_capacity_mah=round(usable_mah, 1) if usable_mah else None,
            lifetime_hours=round(lifetime_hours, 1) if lifetime_hours else None,
            lifetime_days=round(lifetime_days, 2) if lifetime_days else None,
            recommendations=recommendations,
            using_estimated_values=using_estimated,
        )


def _build_recommendations(
    mcu_ua: float, periph_ua: float, ext_ua: float,
    total_ma: float, lifetime_days: Optional[float],
    mode_breakdown: List[PowerBreakdown],
    peripherals: List[Dict],
) -> List[str]:
    tips = []
    total_ua = mcu_ua + periph_ua + ext_ua

    if total_ua <= 0:
        return ["Add at least one operating mode to compute recommendations."]

    # MCU dominance
    mcu_pct = mcu_ua / total_ua * 100
    if mcu_pct > 60:
        tips.append(
            f"MCU accounts for {mcu_pct:.0f}% of total power. "
            "Increase stop/standby duty to reduce MCU contribution."
        )

    # Check if stop mode is used
    mode_names = {m.mode for m in mode_breakdown}
    if "run" in mode_names and "stop" not in mode_names and "standby" not in mode_names:
        run_pct = next((m.time_percent for m in mode_breakdown if m.mode == "run"), 100)
        if run_pct > 30:
            tips.append(
                f"No stop/standby mode configured. Adding even 70% stop mode could "
                f"reduce average current by ~{int(run_pct * 0.8)}% for battery-powered designs."
            )

    # USB power warning
    peri_types = [p.get("type", "").lower() for p in peripherals]
    if "usb" in peri_types:
        tips.append(
            "USB active: contributes ~3.5mA. Disconnect USB bus when not transferring data "
            "using OTG suspend for sub-mA idle current."
        )
    if "ethernet" in peri_types:
        tips.append(
            "Ethernet PHY active: contributes ~8mA. Use IEEE 802.3az EEE (Energy Efficient Ethernet) "
            "or power-gate the PHY between bursts."
        )

    # CAN warning
    if "can" in peri_types or "can_fd" in peri_types:
        tips.append(
            "CAN active: 650–800µA per instance. In sleep-dominant designs, gate CAN with "
            "a STB pin (most transceivers support <10µA standby mode)."
        )

    # Battery life guidance
    if lifetime_days is not None:
        if lifetime_days < 1:
            tips.append(
                f"⚠️ Battery life < 24 hours ({lifetime_days * 24:.1f}h). "
                "Consider a larger battery, duty-cycling more peripherals, or a lower-power MCU family (STM32L-series)."
            )
        elif lifetime_days < 30:
            tips.append(
                f"Battery life {lifetime_days:.1f} days. For IoT/wearables targeting years of operation, "
                "aim for total average current < 50µA."
            )
        elif lifetime_days > 365:
            tips.append(
                f"✅ Excellent battery life: {lifetime_days:.0f} days ({lifetime_days / 365:.1f} years). "
                "Design is well-optimised for low-power operation."
            )

    # External load dominance
    ext_pct = ext_ua / total_ua * 100
    if ext_pct > 40:
        tips.append(
            f"External components consume {ext_pct:.0f}% of total power. "
            "Review external load duty cycles — power-gate sensors and transceivers when idle."
        )

    if not tips:
        tips.append("✅ Power profile looks well-balanced. No immediate optimisation issues found.")

    return tips


def profile_to_dict(p: PowerProfile) -> dict:
    """Serialize a PowerProfile to a JSON-safe dict."""
    return {
        "mpn": p.mpn,
        "core": p.core,
        "system_voltage_v": p.system_voltage_v,
        "using_estimated_values": p.using_estimated_values,
        "mode_breakdown": [
            {
                "mode": m.mode,
                "current_ua": m.current_ua,
                "time_percent": m.time_percent,
                "weighted_ua": m.weighted_ua,
            }
            for m in p.mode_breakdown
        ],
        "peripheral_breakdown": p.peripheral_breakdown,
        "external_breakdown": p.external_breakdown,
        "totals": {
            "mcu_avg_ua": p.mcu_avg_ua,
            "peripheral_avg_ua": p.peripheral_avg_ua,
            "external_avg_ua": p.external_avg_ua,
            "total_avg_ua": p.total_avg_ua,
            "total_avg_ma": p.total_avg_ma,
        },
        "battery": {
            "capacity_mah": p.battery_capacity_mah,
            "chemistry": p.battery_chemistry,
            "usable_mah": p.usable_capacity_mah,
            "lifetime_hours": p.lifetime_hours,
            "lifetime_days": p.lifetime_days,
        },
        "recommendations": p.recommendations,
    }
