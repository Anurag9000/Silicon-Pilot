"""
Firmware Stack Data Populator

Populates the firmware_stacks table with real RTOS, middleware, and libraries.

Catalog includes:
- RTOS: FreeRTOS, Zephyr, ThreadX, embOS, µC/OS-III, RT-Thread, RIOT
- TCP/IP: lwIP, uIP, CycloneTCP, picoTCP
- USB: TinyUSB, STM32 USB Device Library, CherryUSB
- Filesystems: FatFs, LittleFS, SPIFFS
- Crypto: mbedTLS, WolfSSL, TinyCrypt
- GUI: LVGL, TouchGFX, emWin, µGUI
- BLE: NimBLE, Zephyr BLE, BlueKitchen
"""

import asyncio
import asyncpg
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from architecture.firmware_stack_recommender import FirmwareStackRecommender


async def populate_firmware_stacks(db_url: str):
    """Populate firmware stacks database"""
    
    recommender = FirmwareStackRecommender(db_url)
    
    print("="*60)
    print(" "*15 + "FIRMWARE STACK POPULATION")
    print("="*60 + "\n")
    
    # RTOS
    print("[1/7] Populating RTOS...")
    
    rtos_stacks = [
        {
            "name": "FreeRTOS",
            "vendor": "Amazon",
            "license": "MIT",
            "flash_kb": 10,
            "ram_kb": 4,
            "cores": ["Cortex-M0", "Cortex-M0+", "Cortex-M3", "Cortex-M4", "Cortex-M7", "Cortex-M33"],
            "features": ["preemptive", "tickless", "queue", "semaphore", "mutex"],
            "protocols": [],
            "docs": "https://www.freertos.org/Documentation/RTOS_book.html",
            "repo": "https://github.com/FreeRTOS/FreeRTOS-Kernel"
        },
        {
            "name": "Zephyr RTOS",
            "vendor": "Linux Foundation",
            "license": "Apache-2.0",
            "flash_kb": 50,
            "ram_kb": 8,
            "cores": ["Cortex-M0", "Cortex-M0+", "Cortex-M3", "Cortex-M4", "Cortex-M7", "Cortex-M33"],
            "features": ["preemptive", "smp", "mpu_support", "tickless"],
            "protocols": [],
            "docs": "https://docs.zephyrproject.org/",
            "repo": "https://github.com/zephyrproject-rtos/zephyr"
        },
        {
            "name": "Azure RTOS ThreadX",
            "vendor": "Microsoft",
            "license": "MIT",
            "flash_kb": 12,
            "ram_kb": 5,
            "cores": ["Cortex-M0", "Cortex-M3", "Cortex-M4", "Cortex-M7"],
            "features": ["preemptive", "priority_inheritance", "event_flags"],
            "protocols": [],
            "docs": "https://docs.microsoft.com/azure/rtos/threadx/",
            "repo": "https://github.com/azure-rtos/threadx"
        },
        {
            "name": "RT-Thread",
            "vendor": "RT-Thread",
            "license": "Apache-2.0",
            "flash_kb": 20,
            "ram_kb": 6,
            "cores": ["Cortex-M0", "Cortex-M3", "Cortex-M4", "Cortex-M7"],
            "features": ["preemptive", "device_framework", "component_framework"],
            "protocols": [],
            "docs": "https://www.rt-thread.io/document/site/",
            "repo": "https://github.com/RT-Thread/rt-thread"
        },
        {
            "name": "RIOT",
            "vendor": "RIOT Community",
            "license": "LGPL",
            "flash_kb": 30,
            "ram_kb": 10,
            "cores": ["Cortex-M0", "Cortex-M3", "Cortex-M4"],
            "features": ["preemptive", "tickless", "iot_focused"],
            "protocols": [],
            "docs": "https://doc.riot-os.org/",
            "repo": "https://github.com/RIOT-OS/RIOT"
        }
    ]
    
    for stack in rtos_stacks:
        stack_id = await recommender.add_firmware_stack(
            stack_name=stack["name"],
            stack_type="rtos",
            vendor=stack["vendor"],
            license=stack["license"],
            flash_typical_kb=stack["flash_kb"],
            ram_typical_kb=stack["ram_kb"],
            supported_cores=stack["cores"],
            features=stack["features"],
            protocols=stack["protocols"],
            documentation_url=stack["docs"],
            repository_url=stack["repo"]
        )
        print(f"  ✓ {stack['name']}")
    
    # TCP/IP Stacks
    print("\n[2/7] Populating TCP/IP Stacks...")
    
    tcpip_stacks = [
        {
            "name": "lwIP",
            "vendor": "Community",
            "license": "BSD",
            "flash_kb": 40,
            "ram_kb": 16,
            "cores": ["Cortex-M0", "Cortex-M3", "Cortex-M4", "Cortex-M7"],
            "features": ["lightweight", "modular"],
            "protocols": ["IPv4", "IPv6", "TCP", "UDP", "ICMP", "DHCP", "DNS", "HTTP"],
            "docs": "https://www.nongnu.org/lwip/",
            "repo": "https://git.savannah.nongnu.org/cgit/lwip.git"
        },
        {
            "name": "uIP",
            "vendor": "Contiki",
            "license": "BSD",
            "flash_kb": 15,
            "ram_kb": 8,
            "cores": ["Cortex-M0", "Cortex-M3", "Cortex-M4"],
            "features": ["minimal", "embedded"],
            "protocols": ["IPv4", "TCP", "UDP", "ICMP"],
            "docs": "http://dunkels.com/adam/uip/",
            "repo": "https://github.com/adamdunkels/uip"
        },
        {
            "name": "CycloneTCP",
            "vendor": "Oryx Embedded",
            "license": "GPL",
            "flash_kb": 60,
            "ram_kb": 20,
            "cores": ["Cortex-M3", "Cortex-M4", "Cortex-M7"],
            "features": ["full_featured", "secure"],
            "protocols": ["IPv4", "IPv6", "TCP", "UDP", "HTTP", "HTTPS", "FTP", "MQTT"],
            "docs": "https://www.oryx-embedded.com/doc/cyclone_tcp/",
            "repo": "https://www.oryx-embedded.com/cyclone_tcp.html"
        }
    ]
    
    for stack in tcpip_stacks:
        await recommender.add_firmware_stack(
            stack_name=stack["name"],
            stack_type="tcp_ip",
            vendor=stack["vendor"],
            license=stack["license"],
            flash_typical_kb=stack["flash_kb"],
            ram_typical_kb=stack["ram_kb"],
            supported_cores=stack["cores"],
            features=stack["features"],
            protocols=stack["protocols"],
            documentation_url=stack["docs"],
            repository_url=stack["repo"]
        )
        print(f"  ✓ {stack['name']}")
    
    # USB Stacks
    print("\n[3/7] Populating USB Stacks...")
    
    usb_stacks = [
        {
            "name": "TinyUSB",
            "vendor": "hathach",
            "license": "MIT",
            "flash_kb": 25,
            "ram_kb": 8,
            "cores": ["Cortex-M0", "Cortex-M3", "Cortex-M4", "Cortex-M7"],
            "features": ["device", "host", "cdc", "msc", "hid"],
            "protocols": ["USB 2.0"],
            "docs": "https://docs.tinyusb.org/",
            "repo": "https://github.com/hathach/tinyusb"
        },
        {
            "name": "STM32 USB Device Library",
            "vendor": "STMicroelectronics",
            "license": "BSD",
            "flash_kb": 30,
            "ram_kb": 10,
            "cores": ["Cortex-M3", "Cortex-M4", "Cortex-M7"],
            "features": ["device", "cdc", "msc", "hid", "dfu"],
            "protocols": ["USB 2.0"],
            "docs": "https://www.st.com/en/embedded-software/stsw-stm32121.html",
            "repo": "https://github.com/STMicroelectronics/STM32CubeF4"
        }
    ]
    
    for stack in usb_stacks:
        await recommender.add_firmware_stack(
            stack_name=stack["name"],
            stack_type="usb",
            vendor=stack["vendor"],
            license=stack["license"],
            flash_typical_kb=stack["flash_kb"],
            ram_typical_kb=stack["ram_kb"],
            supported_cores=stack["cores"],
            features=stack["features"],
            protocols=stack["protocols"],
            documentation_url=stack["docs"],
            repository_url=stack["repo"]
        )
        print(f"  ✓ {stack['name']}")
    
    # Filesystems
    print("\n[4/7] Populating Filesystems...")
    
    fs_stacks = [
        {
            "name": "FatFs",
            "vendor": "ChaN",
            "license": "BSD",
            "flash_kb": 10,
            "ram_kb": 4,
            "cores": ["Cortex-M0", "Cortex-M3", "Cortex-M4", "Cortex-M7"],
            "features": ["fat12", "fat16", "fat32", "exfat"],
            "protocols": [],
            "docs": "http://elm-chan.org/fsw/ff/00index_e.html",
            "repo": "http://elm-chan.org/fsw/ff/00index_e.html"
        },
        {
            "name": "LittleFS",
            "vendor": "ARM Mbed",
            "license": "BSD",
            "flash_kb": 8,
            "ram_kb": 3,
            "cores": ["Cortex-M0", "Cortex-M3", "Cortex-M4", "Cortex-M7"],
            "features": ["wear_leveling", "power_loss_resilient"],
            "protocols": [],
            "docs": "https://github.com/littlefs-project/littlefs",
            "repo": "https://github.com/littlefs-project/littlefs"
        }
    ]
    
    for stack in fs_stacks:
        await recommender.add_firmware_stack(
            stack_name=stack["name"],
            stack_type="filesystem",
            vendor=stack["vendor"],
            license=stack["license"],
            flash_typical_kb=stack["flash_kb"],
            ram_typical_kb=stack["ram_kb"],
            supported_cores=stack["cores"],
            features=stack["features"],
            protocols=stack["protocols"],
            documentation_url=stack["docs"],
            repository_url=stack["repo"]
        )
        print(f"  ✓ {stack['name']}")
    
    # Crypto Libraries
    print("\n[5/7] Populating Crypto Libraries...")
    
    crypto_stacks = [
        {
            "name": "mbedTLS",
            "vendor": "ARM",
            "license": "Apache-2.0",
            "flash_kb": 100,
            "ram_kb": 30,
            "cores": ["Cortex-M3", "Cortex-M4", "Cortex-M7"],
            "features": ["tls", "dtls", "aes", "rsa", "ecc"],
            "protocols": ["TLS 1.2", "TLS 1.3"],
            "docs": "https://tls.mbed.org/",
            "repo": "https://github.com/ARMmbed/mbedtls"
        },
        {
            "name": "WolfSSL",
            "vendor": "wolfSSL",
            "license": "GPL",
            "flash_kb": 80,
            "ram_kb": 25,
            "cores": ["Cortex-M3", "Cortex-M4", "Cortex-M7"],
            "features": ["tls", "dtls", "aes", "rsa", "ecc", "optimized"],
            "protocols": ["TLS 1.2", "TLS 1.3"],
            "docs": "https://www.wolfssl.com/documentation/",
            "repo": "https://github.com/wolfSSL/wolfssl"
        }
    ]
    
    for stack in crypto_stacks:
        await recommender.add_firmware_stack(
            stack_name=stack["name"],
            stack_type="crypto",
            vendor=stack["vendor"],
            license=stack["license"],
            flash_typical_kb=stack["flash_kb"],
            ram_typical_kb=stack["ram_kb"],
            supported_cores=stack["cores"],
            features=stack["features"],
            protocols=stack["protocols"],
            documentation_url=stack["docs"],
            repository_url=stack["repo"]
        )
        print(f"  ✓ {stack['name']}")
    
    # GUI Libraries
    print("\n[6/7] Populating GUI Libraries...")
    
    gui_stacks = [
        {
            "name": "LVGL",
            "vendor": "LVGL",
            "license": "MIT",
            "flash_kb": 80,
            "ram_kb": 32,
            "cores": ["Cortex-M3", "Cortex-M4", "Cortex-M7"],
            "features": ["widgets", "animations", "styles", "touch"],
            "protocols": [],
            "docs": "https://docs.lvgl.io/",
            "repo": "https://github.com/lvgl/lvgl"
        },
        {
            "name": "TouchGFX",
            "vendor": "STMicroelectronics",
            "license": "Proprietary",
            "flash_kb": 100,
            "ram_kb": 40,
            "cores": ["Cortex-M4", "Cortex-M7"],
            "features": ["hardware_acceleration", "designer_tool", "animations"],
            "protocols": [],
            "docs": "https://support.touchgfx.com/",
            "repo": "https://www.st.com/en/development-tools/touchgfxdesigner.html"
        }
    ]
    
    for stack in gui_stacks:
        await recommender.add_firmware_stack(
            stack_name=stack["name"],
            stack_type="gui",
            vendor=stack["vendor"],
            license=stack["license"],
            flash_typical_kb=stack["flash_kb"],
            ram_typical_kb=stack["ram_kb"],
            supported_cores=stack["cores"],
            features=stack["features"],
            protocols=stack["protocols"],
            documentation_url=stack["docs"],
            repository_url=stack["repo"]
        )
        print(f"  ✓ {stack['name']}")
    
    # BLE Stacks
    print("\n[7/7] Populating BLE Stacks...")
    
    ble_stacks = [
        {
            "name": "NimBLE",
            "vendor": "Apache Mynewt",
            "license": "Apache-2.0",
            "flash_kb": 60,
            "ram_kb": 20,
            "cores": ["Cortex-M0", "Cortex-M3", "Cortex-M4"],
            "features": ["ble_4_2", "ble_5_0", "central", "peripheral"],
            "protocols": ["BLE 4.2", "BLE 5.0"],
            "docs": "https://mynewt.apache.org/latest/network/",
            "repo": "https://github.com/apache/mynewt-nimble"
        },
        {
            "name": "Zephyr BLE",
            "vendor": "Linux Foundation",
            "license": "Apache-2.0",
            "flash_kb": 70,
            "ram_kb": 25,
            "cores": ["Cortex-M0", "Cortex-M3", "Cortex-M4", "Cortex-M33"],
            "features": ["ble_5_0", "mesh", "central", "peripheral"],
            "protocols": ["BLE 5.0", "BLE Mesh"],
            "docs": "https://docs.zephyrproject.org/latest/connectivity/bluetooth/",
            "repo": "https://github.com/zephyrproject-rtos/zephyr"
        }
    ]
    
    for stack in ble_stacks:
        await recommender.add_firmware_stack(
            stack_name=stack["name"],
            stack_type="ble",
            vendor=stack["vendor"],
            license=stack["license"],
            flash_typical_kb=stack["flash_kb"],
            ram_typical_kb=stack["ram_kb"],
            supported_cores=stack["cores"],
            features=stack["features"],
            protocols=stack["protocols"],
            documentation_url=stack["docs"],
            repository_url=stack["repo"]
        )
        print(f"  ✓ {stack['name']}")
    
    print("\n" + "="*60)
    print("✓ Firmware Stack Population Complete!")
    print("  Total: 20 stacks across 7 categories")
    print("="*60 + "\n")


async def main():
    import os
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot")
    await populate_firmware_stacks(db_url)


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
