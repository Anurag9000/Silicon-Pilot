"""
Power Budget Calculator

Calculates system power consumption and battery life.

Features:
- MCU power in different modes (Run, Sleep, Stop, Standby)
- Peripheral power consumption
- External component power
- Duty cycle analysis
- Battery life estimation
- Power optimization recommendations

Supports:
- Multiple operating modes with time percentages
- Dynamic frequency scaling
- Peripheral duty cycles
- Battery capacity and chemistry
"""

import asyncpg
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import uuid


class PowerMode(Enum):
    """MCU operating modes"""
    RUN = "run"
    SLEEP = "sleep"
    STOP = "stop"
    STANDBY = "standby"
    SHUTDOWN = "shutdown"


@dataclass
class ModeProfile:
    """Operating mode profile"""
    mode: PowerMode
    duration_percent: float  # Percentage of time in this mode
    frequency_mhz: Optional[float] = None
    active_peripherals: List[str] = None


@dataclass
class PeripheralUsage:
    """Peripheral usage profile"""
    peripheral_type: str
    peripheral_instance: str
    duty_cycle_percent: float  # Percentage of time active


@dataclass
class ExternalComponent:
    """External component power"""
    name: str
    voltage_v: float
    current_ma: float
    duty_cycle_percent: float = 100.0


@dataclass
class PowerBudget:
    """Complete power budget"""
    mcu_power_uw: float
    peripheral_power_uw: float
    external_power_uw: float
    total_power_uw: float
    total_current_ma: float
    breakdown: Dict[str, float]


@dataclass
class BatteryLife:
    """Battery life estimation"""
    capacity_mah: float
    average_current_ma: float
    lifetime_hours: float
    lifetime_days: float
    recommendations: List[str]


class PowerBudgetCalculator:
    """Calculate system power consumption"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def get_mcu_power(self, part_id: uuid.UUID, mode: PowerMode,
                           frequency_mhz: Optional[float] = None) -> Optional[float]:
        """
        Get MCU power consumption for a mode
        
        Returns power in microwatts (µW)
        """
        async with self.db_pool.acquire() as conn:
            # Get power data for mode
            power_data = await conn.fetchrow("""
                SELECT voltage_v, current_typ_ua, frequency_mhz
                FROM power_modes
                WHERE part_id = $1 AND mode_name = $2
                ORDER BY ABS(COALESCE(frequency_mhz, 0) - COALESCE($3, 0))
                LIMIT 1
            """, part_id, mode.value, frequency_mhz)
            
            if not power_data:
                return None
            
            # Power = Voltage × Current
            power_uw = power_data['voltage_v'] * power_data['current_typ_ua']
            return power_uw
    
    async def get_peripheral_power(self, part_id: uuid.UUID,
                                   peripheral_type: str,
                                   peripheral_instance: Optional[str] = None) -> Optional[float]:
        """
        Get peripheral power consumption
        
        Returns power in microwatts (µW)
        """
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT current_typ_ua
                FROM peripheral_power
                WHERE part_id = $1 AND peripheral_type = $2
            """
            params = [part_id, peripheral_type]
            
            if peripheral_instance:
                query += " AND peripheral_instance = $3"
                params.append(peripheral_instance)
            
            query += " LIMIT 1"
            
            result = await conn.fetchval(query, *params)
            
            if result:
                # Assume 3.3V for peripherals
                return 3.3 * result
            return None
    
    async def calculate_mcu_power(self, part_id: uuid.UUID,
                                 mode_profiles: List[ModeProfile]) -> Dict[str, float]:
        """
        Calculate average MCU power across multiple modes
        
        Returns:
            {
                'run': power_uw,
                'sleep': power_uw,
                'average': power_uw
            }
        """
        mode_powers = {}
        total_power = 0.0
        
        for profile in mode_profiles:
            power = await self.get_mcu_power(part_id, profile.mode, profile.frequency_mhz)
            
            if power is None:
                # Estimate if no data available
                if profile.mode == PowerMode.RUN:
                    power = 10000.0  # 10mW typical
                elif profile.mode == PowerMode.SLEEP:
                    power = 1000.0  # 1mW typical
                elif profile.mode == PowerMode.STOP:
                    power = 100.0  # 100µW typical
                else:
                    power = 10.0  # 10µW typical
            
            mode_powers[profile.mode.value] = power
            total_power += power * (profile.duration_percent / 100.0)
        
        mode_powers['average'] = total_power
        return mode_powers
    
    async def calculate_peripheral_power(self, part_id: uuid.UUID,
                                        peripheral_usage: List[PeripheralUsage]) -> Dict[str, float]:
        """Calculate peripheral power consumption"""
        peripheral_powers = {}
        total_power = 0.0
        
        for usage in peripheral_usage:
            power = await self.get_peripheral_power(
                part_id, 
                usage.peripheral_type,
                usage.peripheral_instance
            )
            
            if power is None:
                # Estimate based on peripheral type
                estimates = {
                    'uart': 500.0,  # 500µW
                    'spi': 800.0,
                    'i2c': 400.0,
                    'adc': 1000.0,
                    'dac': 1200.0,
                    'timer': 300.0,
                    'can': 2000.0,
                    'usb': 5000.0
                }
                power = estimates.get(usage.peripheral_type.lower(), 500.0)
            
            # Apply duty cycle
            effective_power = power * (usage.duty_cycle_percent / 100.0)
            peripheral_powers[f"{usage.peripheral_type}_{usage.peripheral_instance}"] = effective_power
            total_power += effective_power
        
        peripheral_powers['total'] = total_power
        return peripheral_powers
    
    def calculate_external_power(self, components: List[ExternalComponent]) -> Dict[str, float]:
        """Calculate external component power"""
        component_powers = {}
        total_power = 0.0
        
        for comp in components:
            # Power = Voltage × Current (convert mA to µA, then to µW)
            power_uw = comp.voltage_v * comp.current_ma * 1000.0
            effective_power = power_uw * (comp.duty_cycle_percent / 100.0)
            
            component_powers[comp.name] = effective_power
            total_power += effective_power
        
        component_powers['total'] = total_power
        return component_powers
    
    async def calculate_total_budget(self, part_id: uuid.UUID,
                                     mode_profiles: List[ModeProfile],
                                     peripheral_usage: List[PeripheralUsage],
                                     external_components: List[ExternalComponent],
                                     system_voltage_v: float = 3.3) -> PowerBudget:
        """Calculate complete power budget"""
        
        # Calculate each component
        mcu_powers = await self.calculate_mcu_power(part_id, mode_profiles)
        peripheral_powers = await self.calculate_peripheral_power(part_id, peripheral_usage)
        external_powers = self.calculate_external_power(external_components)
        
        # Sum totals
        mcu_total = mcu_powers['average']
        peripheral_total = peripheral_powers['total']
        external_total = external_powers['total']
        total_power_uw = mcu_total + peripheral_total + external_total
        
        # Convert to current (I = P / V)
        total_current_ma = (total_power_uw / 1000.0) / system_voltage_v
        
        # Build breakdown
        breakdown = {
            'mcu': mcu_total,
            'peripherals': peripheral_total,
            'external': external_total
        }
        breakdown.update({f"mcu_{k}": v for k, v in mcu_powers.items() if k != 'average'})
        breakdown.update({k: v for k, v in peripheral_powers.items() if k != 'total'})
        breakdown.update({k: v for k, v in external_powers.items() if k != 'total'})
        
        return PowerBudget(
            mcu_power_uw=mcu_total,
            peripheral_power_uw=peripheral_total,
            external_power_uw=external_total,
            total_power_uw=total_power_uw,
            total_current_ma=total_current_ma,
            breakdown=breakdown
        )
    
    def estimate_battery_life(self, budget: PowerBudget,
                              battery_capacity_mah: float,
                              battery_chemistry: str = "Li-Ion") -> BatteryLife:
        """
        Estimate battery life
        
        Args:
            budget: Power budget
            battery_capacity_mah: Battery capacity in mAh
            battery_chemistry: "Li-Ion", "Li-Po", "Alkaline", "NiMH"
        """
        # Derating factors for different chemistries
        derating = {
            "Li-Ion": 0.85,  # 85% usable capacity
            "Li-Po": 0.85,
            "Alkaline": 0.70,  # 70% usable capacity
            "NiMH": 0.80
        }
        
        usable_capacity = battery_capacity_mah * derating.get(battery_chemistry, 0.80)
        
        # Battery life = Capacity / Current
        lifetime_hours = usable_capacity / budget.total_current_ma
        lifetime_days = lifetime_hours / 24.0
        
        # Generate recommendations
        recommendations = []
        
        if lifetime_days < 1:
            recommendations.append("Battery life < 1 day. Consider larger battery or reduce power consumption.")
        
        if budget.mcu_power_uw > budget.total_power_uw * 0.5:
            recommendations.append("MCU consumes >50% of power. Consider lower power modes or frequency scaling.")
        
        if budget.external_power_uw > budget.total_power_uw * 0.3:
            recommendations.append("External components consume >30% of power. Review component selection.")
        
        if budget.total_current_ma > 100:
            recommendations.append(f"High average current ({budget.total_current_ma:.1f}mA). Optimize duty cycles.")
        
        return BatteryLife(
            capacity_mah=battery_capacity_mah,
            average_current_ma=budget.total_current_ma,
            lifetime_hours=lifetime_hours,
            lifetime_days=lifetime_days,
            recommendations=recommendations
        )


# Example usage
async def main():
    import os
    import asyncpg
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")
    pool = await asyncpg.create_pool(db_url)
    calculator = PowerBudgetCalculator(pool)
    
    # Example: Calculate power budget
    # mode_profiles = [
    #     ModeProfile(PowerMode.RUN, duration_percent=10, frequency_mhz=168),
    #     ModeProfile(PowerMode.SLEEP, duration_percent=80),
    #     ModeProfile(PowerMode.STOP, duration_percent=10)
    # ]
    # 
    # peripheral_usage = [
    #     PeripheralUsage("uart", "USART1", duty_cycle_percent=5),
    #     PeripheralUsage("spi", "SPI1", duty_cycle_percent=2),
    #     PeripheralUsage("adc", "ADC1", duty_cycle_percent=1)
    # ]
    # 
    # external_components = [
    #     ExternalComponent("LED", voltage_v=3.3, current_ma=2, duty_cycle_percent=10),
    #     ExternalComponent("Sensor", voltage_v=3.3, current_ma=0.5, duty_cycle_percent=100)
    # ]
    # 
    # budget = await calculator.calculate_total_budget(
    #     part_id, mode_profiles, peripheral_usage, external_components
    # )
    # 
    # print(f"Total Power: {budget.total_power_uw / 1000:.2f} mW")
    # print(f"Average Current: {budget.total_current_ma:.2f} mA")
    # 
    # battery_life = calculator.estimate_battery_life(budget, battery_capacity_mah=2000)
    # print(f"\nBattery Life: {battery_life.lifetime_days:.1f} days")
    # for rec in battery_life.recommendations:
    #     print(f"  • {rec}")


if __name__ == "__main__":
    import asyncio
    import sys
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
