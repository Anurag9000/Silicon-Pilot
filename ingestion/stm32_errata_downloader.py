"""
STM32 Errata Sheet Downloader

Downloads errata sheets for STM32 parts. Errata sheets document silicon bugs,
limitations, and workarounds.
"""

import requests
import time
from pathlib import Path
from typing import Dict, List
import json

class STM32ErrataDownloader:
    """Download STM32 errata sheets from ST.com"""
    
    def __init__(self, output_dir: str = "data/stm32_errata"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Errata sheet URLs for major parts
        # Format: part_number -> {es_number, url, description}
        self.part_errata = {
            # STM32F0 Series
            "STM32F030": {
                "es_number": "ES0251",
                "url": "https://www.st.com/resource/en/errata_sheet/es0251-stm32f030x4x6x8xc-device-errata-stmicroelectronics.pdf",
                "description": "STM32F030 Errata"
            },
            "STM32F072": {
                "es_number": "ES0206",
                "url": "https://www.st.com/resource/en/errata_sheet/es0206-stm32f07xxx-device-errata-stmicroelectronics.pdf",
                "description": "STM32F072 Errata"
            },
            
            # STM32F1 Series
            "STM32F103": {
                "es_number": "ES0091",
                "url": "https://www.st.com/resource/en/errata_sheet/es0091-stm32f101xc-stm32f101xd-stm32f101xe-stm32f103xc-stm32f103xd-and-stm32f103xe-highdensity-device-errata-stmicroelectronics.pdf",
                "description": "STM32F103 Errata"
            },
            
            # STM32F2 Series
            "STM32F205": {
                "es_number": "ES0182",
                "url": "https://www.st.com/resource/en/errata_sheet/es0182-stm32f205xx-and-stm32f207xx-device-errata-stmicroelectronics.pdf",
                "description": "STM32F205/F207 Errata"
            },
            
            # STM32F3 Series
            "STM32F303": {
                "es_number": "ES0202",
                "url": "https://www.st.com/resource/en/errata_sheet/es0202-stm32f303xb-stm32f303xc-stm32f303xd-and-stm32f303xe-device-errata-stmicroelectronics.pdf",
                "description": "STM32F303 Errata"
            },
            
            # STM32F4 Series
            "STM32F405": {
                "es_number": "ES0206",
                "url": "https://www.st.com/resource/en/errata_sheet/es0206-stm32f405407xx-and-stm32f415417xx-device-errata-stmicroelectronics.pdf",
                "description": "STM32F405/F407 Errata"
            },
            "STM32F429": {
                "es_number": "ES0182",
                "url": "https://www.st.com/resource/en/errata_sheet/es0182-stm32f427437-and-stm32f429439-line-errata-stmicroelectronics.pdf",
                "description": "STM32F429 Errata"
            },
            
            # STM32F7 Series
            "STM32F746": {
                "es_number": "ES0290",
                "url": "https://www.st.com/resource/en/errata_sheet/es0290-stm32f74xxx-and-stm32f75xxx-device-errata-stmicroelectronics.pdf",
                "description": "STM32F746 Errata"
            },
            
            # STM32H7 Series
            "STM32H743": {
                "es_number": "ES0392",
                "url": "https://www.st.com/resource/en/errata_sheet/es0392-stm32h742xig-stm32h743xig-and-stm32h753xi-device-errata-stmicroelectronics.pdf",
                "description": "STM32H743 Errata"
            },
            "STM32H750": {
                "es_number": "ES0396",
                "url": "https://www.st.com/resource/en/errata_sheet/es0396-stm32h750xb-and-stm32h750vb-device-errata-stmicroelectronics.pdf",
                "description": "STM32H750 Errata"
            },
            
            # STM32L0 Series
            "STM32L051": {
                "es_number": "ES0251",
                "url": "https://www.st.com/resource/en/errata_sheet/es0251-stm32l051x6-stm32l051x8-device-errata-stmicroelectronics.pdf",
                "description": "STM32L051 Errata"
            },
            
            # STM32L1 Series
            "STM32L151": {
                "es_number": "ES0125",
                "url": "https://www.st.com/resource/en/errata_sheet/es0125-stm32l151xc-stm32l151xd-stm32l152xc-stm32l152xd-stm32l162xc-and-stm32l162xd-highdensity-ultralow-power-device-errata-stmicroelectronics.pdf",
                "description": "STM32L151 Errata"
            },
            
            # STM32L4 Series
            "STM32L476": {
                "es_number": "ES0206",
                "url": "https://www.st.com/resource/en/errata_sheet/es0206-stm32l47xxx-and-stm32l48xxx-device-errata-stmicroelectronics.pdf",
                "description": "STM32L476 Errata"
            },
            
            # STM32L5 Series
            "STM32L552": {
                "es_number": "ES0500",
                "url": "https://www.st.com/resource/en/errata_sheet/es0500-stm32l552xx-and-stm32l562xx-device-errata-stmicroelectronics.pdf",
                "description": "STM32L552 Errata"
            },
            
            # STM32G0 Series
            "STM32G071": {
                "es_number": "ES0418",
                "url": "https://www.st.com/resource/en/errata_sheet/es0418-stm32g0x1-device-errata-stmicroelectronics.pdf",
                "description": "STM32G071 Errata"
            },
            
            # STM32G4 Series
            "STM32G474": {
                "es_number": "ES0431",
                "url": "https://www.st.com/resource/en/errata_sheet/es0431-stm32g4-category-3-device-errata-stmicroelectronics.pdf",
                "description": "STM32G474 Errata"
            },
            
            # STM32WB Series
            "STM32WB55": {
                "es_number": "ES0394",
                "url": "https://www.st.com/resource/en/errata_sheet/es0394-stm32wb55xx-device-errata-stmicroelectronics.pdf",
                "description": "STM32WB55 Errata"
            },
            
            # STM32WL Series
            "STM32WLE5": {
                "es_number": "ES0500",
                "url": "https://www.st.com/resource/en/errata_sheet/es0500-stm32wle5xx-device-errata-stmicroelectronics.pdf",
                "description": "STM32WLE5 Errata"
            },
            
            # STM32U5 Series
            "STM32U575": {
                "es_number": "ES0499",
                "url": "https://www.st.com/resource/en/errata_sheet/es0499-stm32u575xx-and-stm32u585xx-device-errata-stmicroelectronics.pdf",
                "description": "STM32U575 Errata"
            },
            
            # STM32H5 Series
            "STM32H563": {
                "es_number": "ES0551",
                "url": "https://www.st.com/resource/en/errata_sheet/es0551-stm32h563xx-device-errata-stmicroelectronics.pdf",
                "description": "STM32H563 Errata"
            },
        }
    
    def download_part(self, part: str) -> bool:
        """Download errata sheet for a part"""
        if part not in self.part_errata:
            print(f"Unknown part: {part}")
            return False
        
        info = self.part_errata[part]
        es_number = info["es_number"]
        url = info["url"]
        description = info["description"]
        
        filename = f"{es_number}_{part}.pdf"
        output_path = self.output_dir / filename
        
        # Skip if already downloaded
        if output_path.exists():
            print(f"[OK] Already exists: {filename}")
            return True
        
        try:
            print(f"[DOWNLOADING] {description} ({es_number})...", end=" ", flush=True)
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
        """Download all errata sheets"""
        results = {}
        
        print(f"\n{'='*60}")
        print(f"Downloading STM32 Errata Sheets")
        print(f"{'='*60}\n")
        
        for part in self.part_errata.keys():
            results[part] = self.download_part(part)
        
        # Save manifest
        manifest = {
            "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "parts": {
                part: {
                    "success": success,
                    "es_number": self.part_errata[part]["es_number"],
                    "description": self.part_errata[part]["description"]
                }
                for part, success in results.items()
            }
        }
        
        manifest_path = self.output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        
        successful = sum(1 for v in results.values() if v)
        print(f"\n{'='*60}")
        print(f"✓ Downloaded {successful}/{len(results)} errata sheets")
        print(f"  Manifest: {manifest_path}")
        print(f"{'='*60}\n")
        
        return results


if __name__ == "__main__":
    downloader = STM32ErrataDownloader()
    results = downloader.download_all()
    
    # Summary
    print("\nSummary:")
    for part, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {part}")
