"""
Reference Design Data Populator

Populates reference_designs table with real designs from:
- STMicroelectronics (Discovery, Nucleo, Evaluation boards)
- Texas Instruments (LaunchPads, EVMs)
- NXP (Freedom, LPCXpresso)
"""

import asyncio
import asyncpg
import uuid
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def populate_reference_designs(db_url: str):
    """Populate reference designs database"""
    
    conn = await asyncpg.connect(db_url)
    
    print("="*60)
    print(" "*15 + "REFERENCE DESIGN POPULATION")
    print("="*60 + "\n")
    
    try:
        # STMicroelectronics Designs
        print("[1/3] Populating ST Reference Designs...")
        
        st_designs = [
            {
                "name": "STM32 IoT Discovery Kit",
                "code": "B-L475E-IOT01A",
                "manufacturer": "STMicroelectronics",
                "application": "IoT",
                "description": "IoT node with WiFi, BLE, NFC, sensors",
                "mcu": "STM32L475VGT6",
                "schematic": "https://www.st.com/resource/en/schematic_pack/b-l475e-iot01ax_sch.zip",
                "bom": "https://www.st.com/resource/en/bill_of_materials/b-l475e-iot01ax_bom.zip"
            },
            {
                "name": "STM32F4 Discovery",
                "code": "STM32F407G-DISC1",
                "manufacturer": "STMicroelectronics",
                "application": "General Purpose",
                "description": "High-performance MCU development board",
                "mcu": "STM32F407VGT6",
                "schematic": "https://www.st.com/resource/en/schematic_pack/stm32f4discovery_sch.zip",
                "bom": "https://www.st.com/resource/en/bill_of_materials/stm32f4discovery_bom.zip"
            },
            {
                "name": "STM32F7 Discovery",
                "code": "STM32F746G-DISCO",
                "manufacturer": "STMicroelectronics",
                "application": "GUI/Display",
                "description": "Discovery kit with 4.3\" LCD touchscreen",
                "mcu": "STM32F746NGH6",
                "schematic": "https://www.st.com/resource/en/schematic_pack/stm32f746g-disco_sch.zip",
                "bom": "https://www.st.com/resource/en/bill_of_materials/stm32f746g-disco_bom.zip"
            },
            {
                "name": "STM32 Nucleo-F401RE",
                "code": "NUCLEO-F401RE",
                "manufacturer": "STMicroelectronics",
                "application": "Prototyping",
                "description": "Low-cost development board with Arduino headers",
                "mcu": "STM32F401RET6",
                "schematic": "https://www.st.com/resource/en/schematic_pack/nucleo_64pins_sch.zip",
                "bom": "https://www.st.com/resource/en/bill_of_materials/nucleo-f401re_bom.zip"
            },
            {
                "name": "STM32 Motor Control Kit",
                "code": "P-NUCLEO-IHM001",
                "manufacturer": "STMicroelectronics",
                "application": "Motor Control",
                "description": "BLDC motor control development kit",
                "mcu": "STM32F302R8T6",
                "schematic": "https://www.st.com/resource/en/schematic_pack/p-nucleo-ihm001_sch.zip",
                "bom": "https://www.st.com/resource/en/bill_of_materials/p-nucleo-ihm001_bom.zip"
            }
        ]
        
        for design in st_designs:
            await conn.execute("""
                INSERT INTO reference_designs (
                    design_name, design_id, manufacturer, application_area,
                    description, schematic_url, bom_url
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, design["name"], design["code"], design["manufacturer"],
                design["application"], design["description"],
                design["schematic"], design["bom"])
            print(f"  ✓ {design['name']}")
        
        # Texas Instruments Designs
        print("\n[2/3] Populating TI Reference Designs...")
        
        ti_designs = [
            {
                "name": "MSP432 LaunchPad",
                "code": "MSP-EXP432P401R",
                "manufacturer": "Texas Instruments",
                "application": "Low Power",
                "description": "Ultra-low-power ARM Cortex-M4F LaunchPad",
                "mcu": "MSP432P401R",
                "schematic": "https://www.ti.com/lit/zip/slau597",
                "bom": "https://www.ti.com/lit/zip/slau597"
            },
            {
                "name": "SimpleLink CC3220 LaunchPad",
                "code": "CC3220SF-LAUNCHXL",
                "manufacturer": "Texas Instruments",
                "application": "WiFi IoT",
                "description": "WiFi and Internet-of-Things solution",
                "mcu": "CC3220SF",
                "schematic": "https://www.ti.com/lit/zip/swru463",
                "bom": "https://www.ti.com/lit/zip/swru463"
            },
            {
                "name": "TM4C123G LaunchPad",
                "code": "EK-TM4C123GXL",
                "manufacturer": "Texas Instruments",
                "application": "General Purpose",
                "description": "Tiva C Series ARM Cortex-M4 LaunchPad",
                "mcu": "TM4C123GH6PM",
                "schematic": "https://www.ti.com/lit/zip/spmu296",
                "bom": "https://www.ti.com/lit/zip/spmu296"
            }
        ]
        
        for design in ti_designs:
            await conn.execute("""
                INSERT INTO reference_designs (
                    design_name, design_id, manufacturer, application_area,
                    description, schematic_url, bom_url
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, design["name"], design["code"], design["manufacturer"],
                design["application"], design["description"],
                design["schematic"], design["bom"])
            print(f"  ✓ {design['name']}")
        
        # NXP Designs
        print("\n[3/3] Populating NXP Reference Designs...")
        
        nxp_designs = [
            {
                "name": "FRDM-K64F Freedom Board",
                "code": "FRDM-K64F",
                "manufacturer": "NXP",
                "application": "General Purpose",
                "description": "Kinetis K64 MCU development platform",
                "mcu": "MK64FN1M0VLL12",
                "schematic": "https://www.nxp.com/downloads/en/schematics/FRDM-K64F-SCH.pdf",
                "bom": "https://www.nxp.com/downloads/en/design-support/FRDM-K64F-BOM.xlsx"
            },
            {
                "name": "LPCXpresso55S69",
                "code": "LPC55S69-EVK",
                "manufacturer": "NXP",
                "application": "Security",
                "description": "LPC55S69 dual-core MCU evaluation board",
                "mcu": "LPC55S69JBD100",
                "schematic": "https://www.nxp.com/downloads/en/schematics/LPCXpresso55S69-SCH.pdf",
                "bom": "https://www.nxp.com/downloads/en/design-support/LPCXpresso55S69-BOM.xlsx"
            },
            {
                "name": "i.MX RT1060 EVK",
                "code": "MIMXRT1060-EVK",
                "manufacturer": "NXP",
                "application": "High Performance",
                "description": "i.MX RT1060 crossover MCU evaluation kit",
                "mcu": "MIMXRT1062DVL6A",
                "schematic": "https://www.nxp.com/downloads/en/schematics/MIMXRT1060-EVK-SCH.pdf",
                "bom": "https://www.nxp.com/downloads/en/design-support/MIMXRT1060-EVK-BOM.xlsx"
            }
        ]
        
        for design in nxp_designs:
            await conn.execute("""
                INSERT INTO reference_designs (
                    design_name, design_id, manufacturer, application_area,
                    description, schematic_url, bom_url
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, design["name"], design["code"], design["manufacturer"],
                design["application"], design["description"],
                design["schematic"], design["bom"])
            print(f"  ✓ {design['name']}")
        
        print("\n" + "="*60)
        print("✓ Reference Design Population Complete!")
        print("  Total: 11 designs (5 ST + 3 TI + 3 NXP)")
        print("="*60 + "\n")
        
    finally:
        await conn.close()


async def main():
    import os
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot")
    await populate_reference_designs(db_url)


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
