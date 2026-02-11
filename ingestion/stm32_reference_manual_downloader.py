"""
STM32 Reference Manual Downloader

Downloads reference manuals for STM32 families. Reference manuals contain
detailed peripheral descriptions, register maps, and programming guides.
"""

import requests
import time
from pathlib import Path
from typing import Dict, List
import json

class STM32ReferenceManualDownloader:
    """Download STM32 reference manuals from ST.com"""
    
    def __init__(self, output_dir: str = "data/stm32_reference_manuals"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Reference Manual URLs (RM numbers from ST documentation)
        self.family_ref_manuals = {
            # STM32F0 Series
            "STM32F0": {
                "rm_number": "RM0360",
                "url": "https://www.st.com/resource/en/reference_manual/rm0360-stm32f030x4x6x8xc-and-stm32f070x6xb-advanced-armbased-32bit-mcus-stmicroelectronics.pdf",
                "description": "STM32F0x0 Reference Manual"
            },
            
            # STM32F1 Series
            "STM32F1": {
                "rm_number": "RM0008",
                "url": "https://www.st.com/resource/en/reference_manual/rm0008-stm32f101xx-stm32f102xx-stm32f103xx-stm32f105xx-and-stm32f107xx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf",
                "description": "STM32F1 Reference Manual"
            },
            
            # STM32F2 Series
            "STM32F2": {
                "rm_number": "RM0033",
                "url": "https://www.st.com/resource/en/reference_manual/rm0033-stm32f205xx-stm32f207xx-stm32f215xx-and-stm32f217xx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf",
                "description": "STM32F2 Reference Manual"
            },
            
            # STM32F3 Series
            "STM32F3": {
                "rm_number": "RM0316",
                "url": "https://www.st.com/resource/en/reference_manual/rm0316-stm32f303xbcde-and-stm32f358xc-advanced-armbased-32bit-mcus-stmicroelectronics.pdf",
                "description": "STM32F3 Reference Manual"
            },
            
            # STM32F4 Series
            "STM32F4": {
                "rm_number": "RM0090",
                "url": "https://www.st.com/resource/en/reference_manual/rm0090-stm32f405415-stm32f407417-stm32f427437-and-stm32f429439-advanced-armbased-32bit-mcus-stmicroelectronics.pdf",
                "description": "STM32F4 Reference Manual"
            },
            
            # STM32F7 Series
            "STM32F7": {
                "rm_number": "RM0385",
                "url": "https://www.st.com/resource/en/reference_manual/rm0385-stm32f75xxx-and-stm32f74xxx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf",
                "description": "STM32F7 Reference Manual"
            },
            
            # STM32H7 Series
            "STM32H7": {
                "rm_number": "RM0433",
                "url": "https://www.st.com/resource/en/reference_manual/rm0433-stm32h742-stm32h743753-and-stm32h750-value-line-advanced-armbased-32bit-mcus-stmicroelectronics.pdf",
                "description": "STM32H7 Reference Manual"
            },
            
            # STM32L0 Series
            "STM32L0": {
                "rm_number": "RM0377",
                "url": "https://www.st.com/resource/en/reference_manual/rm0377-ultralowpower-stm32l0x1-advanced-armbased-32bit-mcus-stmicroelectronics.pdf",
                "description": "STM32L0 Reference Manual"
            },
            
            # STM32L1 Series
            "STM32L1": {
                "rm_number": "RM0038",
                "url": "https://www.st.com/resource/en/reference_manual/rm0038-stm32l100xx-stm32l151xx-stm32l152xx-and-stm32l162xx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf",
                "description": "STM32L1 Reference Manual"
            },
            
            # STM32L4 Series
            "STM32L4": {
                "rm_number": "RM0351",
                "url": "https://www.st.com/resource/en/reference_manual/rm0351-stm32l47xxx-stm32l48xxx-stm32l49xxx-and-stm32l4axxx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf",
                "description": "STM32L4 Reference Manual"
            },
            
            # STM32L5 Series
            "STM32L5": {
                "rm_number": "RM0438",
                "url": "https://www.st.com/resource/en/reference_manual/rm0438-stm32l552xx-and-stm32l562xx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf",
                "description": "STM32L5 Reference Manual"
            },
            
            # STM32G0 Series
            "STM32G0": {
                "rm_number": "RM0444",
                "url": "https://www.st.com/resource/en/reference_manual/rm0444-stm32g0x1-advanced-armbased-32bit-mcus-stmicroelectronics.pdf",
                "description": "STM32G0 Reference Manual"
            },
            
            # STM32G4 Series
            "STM32G4": {
                "rm_number": "RM0440",
                "url": "https://www.st.com/resource/en/reference_manual/rm0440-stm32g4-series-advanced-armbased-32bit-mcus-stmicroelectronics.pdf",
                "description": "STM32G4 Reference Manual"
            },
            
            # STM32WB Series
            "STM32WB": {
                "rm_number": "RM0434",
                "url": "https://www.st.com/resource/en/reference_manual/rm0434-multiprotocol-wireless-32bit-mcu-armbased-cortexm4-with-fpu-bluetooth-lowenergy-and-802154-radio-solution-stmicroelectronics.pdf",
                "description": "STM32WB Reference Manual"
            },
            
            # STM32WL Series
            "STM32WL": {
                "rm_number": "RM0453",
                "url": "https://www.st.com/resource/en/reference_manual/rm0453-stm32wl5x-advanced-armbased-32bit-mcus-with-subghz-radio-solution-stmicroelectronics.pdf",
                "description": "STM32WL Reference Manual"
            },
            
            # STM32U5 Series
            "STM32U5": {
                "rm_number": "RM0456",
                "url": "https://www.st.com/resource/en/reference_manual/rm0456-stm32u5-series-armbased-32bit-mcus-stmicroelectronics.pdf",
                "description": "STM32U5 Reference Manual"
            },
            
            # STM32H5 Series
            "STM32H5": {
                "rm_number": "RM0481",
                "url": "https://www.st.com/resource/en/reference_manual/rm0481-stm32h5-series-armbased-32bit-mcus-stmicroelectronics.pdf",
                "description": "STM32H5 Reference Manual"
            },
        }
    
    def download_family(self, family: str) -> bool:
        """Download reference manual for a family"""
        if family not in self.family_ref_manuals:
            print(f"Unknown family: {family}")
            return False
        
        info = self.family_ref_manuals[family]
        rm_number = info["rm_number"]
        url = info["url"]
        description = info["description"]
        
        filename = f"{rm_number}_{family}.pdf"
        output_path = self.output_dir / filename
        
        # Skip if already downloaded
        if output_path.exists():
            print(f"[OK] Already exists: {filename}")
            return True
        
        try:
            print(f"[DOWNLOADING] {description} ({rm_number})...", end=" ", flush=True)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=30, headers=headers)
            response.raise_for_status()
            
            output_path.write_bytes(response.content)
            print(f"[OK] ({len(response.content) // 1024} KB)")
            time.sleep(2)  # Be respectful to ST servers
            return True
            
        except Exception as e:
            print(f"[WARN] Failed: {e}")
            return False
    
    def download_all(self) -> Dict[str, bool]:
        """Download all reference manuals"""
        results = {}
        
        print(f"\n{'='*60}")
        print(f"Downloading STM32 Reference Manuals")
        print(f"{'='*60}\n")
        
        for family in self.family_ref_manuals.keys():
            results[family] = self.download_family(family)
        
        # Save manifest
        manifest = {
            "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "families": {
                family: {
                    "success": success,
                    "rm_number": self.family_ref_manuals[family]["rm_number"],
                    "description": self.family_ref_manuals[family]["description"]
                }
                for family, success in results.items()
            }
        }
        
        manifest_path = self.output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        
        successful = sum(1 for v in results.values() if v)
        print(f"\n{'='*60}")
        print(f"✓ Downloaded {successful}/{len(results)} reference manuals")
        print(f"  Manifest: {manifest_path}")
        print(f"{'='*60}\n")
        
        return results


if __name__ == "__main__":
    downloader = STM32ReferenceManualDownloader()
    results = downloader.download_all()
    
    # Summary
    print("\nSummary:")
    for family, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {family}")
