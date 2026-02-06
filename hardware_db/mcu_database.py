"""
MCU Database

Parametric database of MCU specifications from major manufacturers.
"""

from typing import List
from .models import MCUSpec, CoreArchitecture, PackageType, StockStatus, PowerConsumption


# STM32 Family
STM32_MCUS = [
    # STM32F0 Series (ARM Cortex-M0)
    MCUSpec(
        part_number="STM32F030F4P6",
        manufacturer="STMicroelectronics",
        family="STM32F0",
        core_architecture=CoreArchitecture.ARM_CORTEX_M0,
        clock_mhz=48,
        ram_kb=4,
        flash_kb=16,
        peripherals=["UART", "SPI", "I2C", "ADC", "GPIO", "TIMER"],
        temp_range=(-40, 85),
        voltage_range=(2.4, 3.6),
        package=PackageType.TQFP,
        pin_count=20,
        cost_usd=0.85,
        stock_status=StockStatus.IN_STOCK,
        power_consumption=PowerConsumption(active_ma=8.5, standby_ua=1.7),
        datasheet_url="https://www.st.com/resource/en/datasheet/stm32f030f4.pdf",
        has_fpu=False
    ),
    
    # STM32F4 Series (ARM Cortex-M4)
    MCUSpec(
        part_number="STM32F405RG",
        manufacturer="STMicroelectronics",
        family="STM32F4",
        core_architecture=CoreArchitecture.ARM_CORTEX_M4,
        clock_mhz=168,
        ram_kb=192,
        flash_kb=1024,
        peripherals=["UART", "SPI", "I2C", "USB", "CAN", "ADC", "DAC", "GPIO", "TIMER", "DMA"],
        temp_range=(-40, 85),
        voltage_range=(1.8, 3.6),
        package=PackageType.LQFP,
        pin_count=64,
        cost_usd=4.20,
        stock_status=StockStatus.IN_STOCK,
        power_consumption=PowerConsumption(active_ma=50, standby_ua=2.0),
        datasheet_url="https://www.st.com/resource/en/datasheet/stm32f405rg.pdf",
        has_fpu=True,
        has_dsp=True
    ),
    
    MCUSpec(
        part_number="STM32F446RE",
        manufacturer="STMicroelectronics",
        family="STM32F4",
        core_architecture=CoreArchitecture.ARM_CORTEX_M4,
        clock_mhz=180,
        ram_kb=128,
        flash_kb=512,
        peripherals=["UART", "SPI", "I2C", "USB", "CAN", "ADC", "DAC", "GPIO", "TIMER", "DMA", "SDIO"],
        temp_range=(-40, 85),
        voltage_range=(1.7, 3.6),
        package=PackageType.LQFP,
        pin_count=64,
        cost_usd=4.50,
        stock_status=StockStatus.IN_STOCK,
        power_consumption=PowerConsumption(active_ma=52, standby_ua=2.1),
        datasheet_url="https://www.st.com/resource/en/datasheet/stm32f446re.pdf",
        has_fpu=True,
        has_dsp=True
    ),
    
    MCUSpec(
        part_number="STM32F407VG",
        manufacturer="STMicroelectronics",
        family="STM32F4",
        core_architecture=CoreArchitecture.ARM_CORTEX_M4,
        clock_mhz=168,
        ram_kb=192,
        flash_kb=1024,
        peripherals=["UART", "SPI", "I2C", "USB", "CAN", "ADC", "DAC", "GPIO", "TIMER", "DMA", "ETHERNET"],
        temp_range=(-40, 85),
        voltage_range=(1.8, 3.6),
        package=PackageType.LQFP,
        pin_count=100,
        cost_usd=6.80,
        stock_status=StockStatus.IN_STOCK,
        power_consumption=PowerConsumption(active_ma=55, standby_ua=2.2),
        datasheet_url="https://www.st.com/resource/en/datasheet/stm32f407vg.pdf",
        has_fpu=True,
        has_dsp=True
    ),
    
    # STM32L4 Series (Ultra-low-power ARM Cortex-M4)
    MCUSpec(
        part_number="STM32L476RG",
        manufacturer="STMicroelectronics",
        family="STM32L4",
        core_architecture=CoreArchitecture.ARM_CORTEX_M4,
        clock_mhz=80,
        ram_kb=128,
        flash_kb=1024,
        peripherals=["UART", "SPI", "I2C", "USB", "CAN", "ADC", "DAC", "GPIO", "TIMER", "DMA"],
        temp_range=(-40, 85),
        voltage_range=(1.71, 3.6),
        package=PackageType.LQFP,
        pin_count=64,
        cost_usd=4.50,
        stock_status=StockStatus.IN_STOCK,
        power_consumption=PowerConsumption(active_ma=6.5, standby_ua=0.29, sleep_ua=0.42, deep_sleep_ua=0.03),
        datasheet_url="https://www.st.com/resource/en/datasheet/stm32l476rg.pdf",
        has_fpu=True,
        has_dsp=True
    ),
    
    # STM32H7 Series (High-performance ARM Cortex-M7)
    MCUSpec(
        part_number="STM32H743ZI",
        manufacturer="STMicroelectronics",
        family="STM32H7",
        core_architecture=CoreArchitecture.ARM_CORTEX_M7,
        clock_mhz=480,
        ram_kb=1024,
        flash_kb=2048,
        peripherals=["UART", "SPI", "I2C", "USB", "CAN", "ETHERNET", "ADC", "DAC", "GPIO", "TIMER", "DMA", "SDIO"],
        temp_range=(-40, 85),
        voltage_range=(1.62, 3.6),
        package=PackageType.LQFP,
        pin_count=144,
        cost_usd=12.50,
        stock_status=StockStatus.IN_STOCK,
        power_consumption=PowerConsumption(active_ma=280, standby_ua=2.95),
        datasheet_url="https://www.st.com/resource/en/datasheet/stm32h743zi.pdf",
        has_fpu=True,
        has_dsp=True,
        has_crypto=True
    ),
]

# ESP32 Family
ESP32_MCUS = [
    MCUSpec(
        part_number="ESP32-WROOM-32",
        manufacturer="Espressif",
        family="ESP32",
        core_architecture=CoreArchitecture.XTENSA_LX6,
        clock_mhz=240,
        ram_kb=520,
        flash_kb=4096,  # External flash
        peripherals=["UART", "SPI", "I2C", "ADC", "DAC", "GPIO", "TIMER", "PWM", "WIFI", "BLUETOOTH"],
        temp_range=(-40, 85),
        voltage_range=(2.2, 3.6),
        package=PackageType.QFN,
        pin_count=38,
        cost_usd=2.50,
        stock_status=StockStatus.IN_STOCK,
        power_consumption=PowerConsumption(active_ma=160, standby_ua=800, sleep_ua=150, deep_sleep_ua=10),
        datasheet_url="https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32_datasheet_en.pdf",
        has_wireless=True
    ),
    
    MCUSpec(
        part_number="ESP32-S3",
        manufacturer="Espressif",
        family="ESP32-S3",
        core_architecture=CoreArchitecture.XTENSA_LX7,
        clock_mhz=240,
        ram_kb=512,
        flash_kb=8192,  # External flash
        peripherals=["UART", "SPI", "I2C", "USB", "ADC", "DAC", "GPIO", "TIMER", "PWM", "WIFI", "BLUETOOTH"],
        temp_range=(-40, 85),
        voltage_range=(3.0, 3.6),
        package=PackageType.QFN,
        pin_count=56,
        cost_usd=2.80,
        stock_status=StockStatus.IN_STOCK,
        power_consumption=PowerConsumption(active_ma=180, standby_ua=850, sleep_ua=160, deep_sleep_ua=7),
        datasheet_url="https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf",
        has_wireless=True,
        has_crypto=True
    ),
    
    MCUSpec(
        part_number="ESP32-C3",
        manufacturer="Espressif",
        family="ESP32-C3",
        core_architecture=CoreArchitecture.RISC_V,
        clock_mhz=160,
        ram_kb=400,
        flash_kb=4096,  # External flash
        peripherals=["UART", "SPI", "I2C", "ADC", "GPIO", "TIMER", "PWM", "WIFI", "BLUETOOTH"],
        temp_range=(-40, 85),
        voltage_range=(3.0, 3.6),
        package=PackageType.QFN,
        pin_count=32,
        cost_usd=1.80,
        stock_status=StockStatus.IN_STOCK,
        power_consumption=PowerConsumption(active_ma=120, standby_ua=750, sleep_ua=130, deep_sleep_ua=5),
        datasheet_url="https://www.espressif.com/sites/default/files/documentation/esp32-c3_datasheet_en.pdf",
        has_wireless=True
    ),
]

# Nordic nRF Series
NRF_MCUS = [
    MCUSpec(
        part_number="nRF52832",
        manufacturer="Nordic Semiconductor",
        family="nRF52",
        core_architecture=CoreArchitecture.ARM_CORTEX_M4,
        clock_mhz=64,
        ram_kb=64,
        flash_kb=512,
        peripherals=["UART", "SPI", "I2C", "ADC", "GPIO", "TIMER", "PWM", "BLUETOOTH"],
        temp_range=(-40, 85),
        voltage_range=(1.7, 3.6),
        package=PackageType.QFN,
        pin_count=48,
        cost_usd=3.20,
        stock_status=StockStatus.IN_STOCK,
        power_consumption=PowerConsumption(active_ma=5.3, standby_ua=0.4, sleep_ua=1.5, deep_sleep_ua=0.3),
        datasheet_url="https://infocenter.nordicsemi.com/pdf/nRF52832_PS_v1.4.pdf",
        has_wireless=True,
        has_fpu=True
    ),
    
    MCUSpec(
        part_number="nRF52840",
        manufacturer="Nordic Semiconductor",
        family="nRF52",
        core_architecture=CoreArchitecture.ARM_CORTEX_M4,
        clock_mhz=64,
        ram_kb=256,
        flash_kb=1024,
        peripherals=["UART", "SPI", "I2C", "USB", "ADC", "GPIO", "TIMER", "PWM", "BLUETOOTH"],
        temp_range=(-40, 85),
        voltage_range=(1.7, 3.6),
        package=PackageType.QFN,
        pin_count=48,
        cost_usd=5.20,
        stock_status=StockStatus.IN_STOCK,
        power_consumption=PowerConsumption(active_ma=4.8, standby_ua=0.4, sleep_ua=1.5, deep_sleep_ua=0.3),
        datasheet_url="https://infocenter.nordicsemi.com/pdf/nRF52840_PS_v1.1.pdf",
        has_wireless=True,
        has_fpu=True,
        has_crypto=True
    ),
]

# Raspberry Pi
RP_MCUS = [
    MCUSpec(
        part_number="RP2040",
        manufacturer="Raspberry Pi",
        family="RP2040",
        core_architecture=CoreArchitecture.ARM_CORTEX_M0_PLUS,
        clock_mhz=133,
        ram_kb=264,
        flash_kb=0,  # External flash required
        peripherals=["UART", "SPI", "I2C", "USB", "ADC", "GPIO", "TIMER", "PWM", "PIO"],
        temp_range=(-40, 85),
        voltage_range=(1.8, 3.3),
        package=PackageType.QFN,
        pin_count=56,
        cost_usd=1.00,
        stock_status=StockStatus.IN_STOCK,
        power_consumption=PowerConsumption(active_ma=30, standby_ua=180),
        datasheet_url="https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf",
        has_fpu=False
    ),
]

# Microchip SAMD Series
SAMD_MCUS = [
    MCUSpec(
        part_number="ATSAMD21G18",
        manufacturer="Microchip",
        family="SAMD21",
        core_architecture=CoreArchitecture.ARM_CORTEX_M0_PLUS,
        clock_mhz=48,
        ram_kb=32,
        flash_kb=256,
        peripherals=["UART", "SPI", "I2C", "USB", "ADC", "DAC", "GPIO", "TIMER", "PWM"],
        temp_range=(-40, 85),
        voltage_range=(1.62, 3.63),
        package=PackageType.TQFP,
        pin_count=48,
        cost_usd=2.10,
        stock_status=StockStatus.IN_STOCK,
        power_consumption=PowerConsumption(active_ma=7.0, standby_ua=0.95),
        datasheet_url="http://ww1.microchip.com/downloads/en/DeviceDoc/SAM_D21_DA1_Family_DataSheet_DS40001882F.pdf",
        has_fpu=False
    ),
    
    MCUSpec(
        part_number="ATSAMD51J19",
        manufacturer="Microchip",
        family="SAMD51",
        core_architecture=CoreArchitecture.ARM_CORTEX_M4,
        clock_mhz=120,
        ram_kb=192,
        flash_kb=512,
        peripherals=["UART", "SPI", "I2C", "USB", "CAN", "ADC", "DAC", "GPIO", "TIMER", "PWM", "DMA"],
        temp_range=(-40, 85),
        voltage_range=(1.71, 3.63),
        package=PackageType.TQFP,
        pin_count=64,
        cost_usd=4.80,
        stock_status=StockStatus.IN_STOCK,
        power_consumption=PowerConsumption(active_ma=36, standby_ua=2.5),
        datasheet_url="http://ww1.microchip.com/downloads/en/DeviceDoc/SAM_D5x_E5x_Family_Data_Sheet_DS60001507G.pdf",
        has_fpu=True,
        has_dsp=True
    ),
]

# Texas Instruments MSP430
MSP430_MCUS = [
    MCUSpec(
        part_number="MSP430FR5994",
        manufacturer="Texas Instruments",
        family="MSP430FR5xxx",
        core_architecture=CoreArchitecture.MSP430,
        clock_mhz=16,
        ram_kb=8,
        flash_kb=256,  # FRAM
        peripherals=["UART", "SPI", "I2C", "ADC", "GPIO", "TIMER"],
        temp_range=(-40, 85),
        voltage_range=(1.8, 3.6),
        package=PackageType.LQFP,
        pin_count=80,
        cost_usd=3.50,
        stock_status=StockStatus.IN_STOCK,
        power_consumption=PowerConsumption(active_ma=1.2, standby_ua=0.35, sleep_ua=0.4, deep_sleep_ua=0.02),
        datasheet_url="https://www.ti.com/lit/ds/symlink/msp430fr5994.pdf",
        has_fpu=False
    ),
]

# Combine all MCUs
ALL_MCUS: List[MCUSpec] = (
    STM32_MCUS +
    ESP32_MCUS +
    NRF_MCUS +
    RP_MCUS +
    SAMD_MCUS +
    MSP430_MCUS
)


def get_all_mcus() -> List[MCUSpec]:
    """Get all MCUs in the database"""
    return ALL_MCUS


def get_mcu_by_part_number(part_number: str) -> MCUSpec:
    """Get a specific MCU by part number"""
    for mcu in ALL_MCUS:
        if mcu.part_number == part_number:
            return mcu
    raise ValueError(f"MCU with part number '{part_number}' not found in database")


def get_mcus_by_manufacturer(manufacturer: str) -> List[MCUSpec]:
    """Get all MCUs from a specific manufacturer"""
    return [mcu for mcu in ALL_MCUS if mcu.manufacturer.lower() == manufacturer.lower()]


def get_mcus_by_family(family: str) -> List[MCUSpec]:
    """Get all MCUs from a specific family"""
    return [mcu for mcu in ALL_MCUS if mcu.family.lower() == family.lower()]


def get_database_stats() -> dict:
    """Get statistics about the MCU database"""
    manufacturers = set(mcu.manufacturer for mcu in ALL_MCUS)
    families = set(mcu.family for mcu in ALL_MCUS)
    architectures = set(mcu.core_architecture for mcu in ALL_MCUS)
    
    return {
        "total_mcus": len(ALL_MCUS),
        "manufacturers": len(manufacturers),
        "families": len(families),
        "architectures": len(architectures),
        "manufacturer_list": sorted(manufacturers),
        "family_list": sorted(families)
    }
