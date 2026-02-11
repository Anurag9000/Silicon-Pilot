"""
STM32 Datasheet Downloader

Downloads STM32 datasheets from ST.com for ingestion.
Focuses on popular families: F0, F1, F4, F7, H7, L4, G4
"""

import requests
import time
from pathlib import Path
from typing import List, Dict
import json

class STM32DatasheetDownloader:
    """Download STM32 datasheets from ST.com"""
    
    def __init__(self, output_dir: str = "data/stm32_datasheets"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # ST.com datasheet URLs for major families
        # These are direct links to family datasheets
        self.family_datasheets = {
            # STM32F0 Series (Cortex-M0)
            "STM32F0": [
                "https://www.st.com/resource/en/datasheet/stm32f030c6.pdf",
                "https://www.st.com/resource/en/datasheet/stm32f051c4.pdf",
                "https://www.st.com/resource/en/datasheet/stm32f072c8.pdf",
            ],
            
            # STM32F1 Series (Cortex-M3)
            "STM32F1": [
                "https://www.st.com/resource/en/datasheet/stm32f103c4.pdf",
                "https://www.st.com/resource/en/datasheet/stm32f103c8.pdf",
                "https://www.st.com/resource/en/datasheet/stm32f103rb.pdf",
            ],
            
            # STM32F4 Series (Cortex-M4)
            "STM32F4": [
                "https://www.st.com/resource/en/datasheet/stm32f401cb.pdf",
                "https://www.st.com/resource/en/datasheet/stm32f405rg.pdf",
                "https://www.st.com/resource/en/datasheet/stm32f407vg.pdf",
                "https://www.st.com/resource/en/datasheet/stm32f429zi.pdf",
            ],
            
            # STM32F7 Series (Cortex-M7)
            "STM32F7": [
                "https://www.st.com/resource/en/datasheet/stm32f722ic.pdf",
                "https://www.st.com/resource/en/datasheet/stm32f746ng.pdf",
                "https://www.st.com/resource/en/datasheet/stm32f767zi.pdf",
            ],
            
            # STM32H7 Series (Cortex-M7, high-performance)
            "STM32H7": [
                "https://www.st.com/resource/en/datasheet/stm32h743bi.pdf",
                "https://www.st.com/resource/en/datasheet/stm32h750ib.pdf",
            ],
            
            # STM32L4 Series (Cortex-M4, low-power)
            "STM32L4": [
                "https://www.st.com/resource/en/datasheet/stm32l432kb.pdf",
                "https://www.st.com/resource/en/datasheet/stm32l476rg.pdf",
            ],
            
            # STM32G4 Series (Cortex-M4, mixed-signal)
            "STM32G4": [
                "https://www.st.com/resource/en/datasheet/stm32g431c6.pdf",
                "https://www.st.com/resource/en/datasheet/stm32g474cb.pdf",
            ],
            
            # STM32F2 Series (Cortex-M3)
            "STM32F2": [
                "https://www.st.com/resource/en/datasheet/stm32f205rb.pdf",
                "https://www.st.com/resource/en/datasheet/stm32f207zg.pdf",
            ],
            
            # STM32F3 Series (Cortex-M4)
            "STM32F3": [
                "https://www.st.com/resource/en/datasheet/stm32f303vc.pdf",
                "https://www.st.com/resource/en/datasheet/stm32f334c8.pdf",
            ],
            
            # STM32L0 Series (Cortex-M0+)
            "STM32L0": [
                "https://www.st.com/resource/en/datasheet/stm32l051c6.pdf",
                "https://www.st.com/resource/en/datasheet/stm32l073rz.pdf",
            ],
            
            # STM32L1 Series (Cortex-M3)
            "STM32L1": [
                "https://www.st.com/resource/en/datasheet/stm32l151c6.pdf",
                "https://www.st.com/resource/en/datasheet/stm32l152re.pdf",
            ],
            
            # STM32G0 Series (Cortex-M0+)
            "STM32G0": [
                "https://www.st.com/resource/en/datasheet/stm32g030c8.pdf",
                "https://www.st.com/resource/en/datasheet/stm32g071rb.pdf",
            ],
            
            # STM32WB Series (Cortex-M4 + M0+, Bluetooth/Zigbee)
            "STM32WB": [
                "https://www.st.com/resource/en/datasheet/stm32wb55cg.pdf",
                "https://www.st.com/resource/en/datasheet/stm32wb15cc.pdf",
            ],
            
            # STM32WL Series (Cortex-M4 + M0+, LoRa)
            "STM32WL": [
                "https://www.st.com/resource/en/datasheet/stm32wle5jc.pdf",
                "https://www.st.com/resource/en/datasheet/stm32wl55cc.pdf",
            ],
            
            # STM32U5 Series (Cortex-M33, Ultra-low power)
            "STM32U5": [
                "https://www.st.com/resource/en/datasheet/stm32u575ci.pdf",
                "https://www.st.com/resource/en/datasheet/stm32u585ci.pdf",
            ],
            
            # STM32C0 Series (Cortex-M0+, Entry Level)
            "STM32C0": [
                "https://www.st.com/resource/en/datasheet/stm32c011f6.pdf",
                "https://www.st.com/resource/en/datasheet/stm32c031c6.pdf",
            ],
            
            # STM32H5 Series (Cortex-M33)
            "STM32H5": [
                "https://www.st.com/resource/en/datasheet/stm32h563zi.pdf",
                "https://www.st.com/resource/en/datasheet/stm32h503cb.pdf",
            ],
            
            # STM32L5 Series (Cortex-M33, Low Power)
            "STM32L5": [
                "https://www.st.com/resource/en/datasheet/stm32l552ze.pdf",
                "https://www.st.com/resource/en/datasheet/stm32l562qe.pdf",
            ],
            
            # STM32U0 Series (Cortex-M0+, Ultra Low Power)
            "STM32U0": [
                "https://www.st.com/resource/en/datasheet/stm32u083rc.pdf", # Hypothetical/Best fit
                "https://www.st.com/resource/en/datasheet/stm32u031c6.pdf",
            ],

            # STM32WBA Series (Cortex-M33, BLE)
            "STM32WBA": [
                "https://www.st.com/resource/en/datasheet/stm32wba52cg.pdf",
            ],
            
            # STM32MP1 Series (Cortex-A7 + M4)
            "STM32MP1": [
                "https://www.st.com/resource/en/datasheet/stm32mp157.pdf",
                "https://www.st.com/resource/en/datasheet/stm32mp135.pdf",
            ],
        }
    
    def download_family(self, family: str) -> List[Path]:
        """Download all datasheets for a family"""
        if family not in self.family_datasheets:
            print(f"Unknown family: {family}")
            return []
        
        downloaded = []
        urls = self.family_datasheets[family]
        
        print(f"\n{'='*60}")
        print(f"Downloading {family} datasheets ({len(urls)} files)")
        print(f"{'='*60}")
        
        for url in urls:
            filename = url.split('/')[-1]
            output_path = self.output_dir / filename
            
            # Skip if already downloaded
            if output_path.exists():
                print(f"[OK] Already exists: {filename}")
                downloaded.append(output_path)
                continue
            
            try:
                print(f"[DOWNLOADING] {filename}...", end=" ", flush=True)
                # Increase timeout and use headers to look more like a browser
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, timeout=5, headers=headers)
                response.raise_for_status()
                
                output_path.write_bytes(response.content)
                print(f"[OK] ({len(response.content) // 1024} KB)")
                downloaded.append(output_path)
                
                # Be respectful to ST.com servers only on success
                time.sleep(2)
                
            except Exception as e:
                print(f"[WARN] Failed to download {filename}: {e}")
                # Check if we have *any* datasheet for this family already
                existing = list(self.output_dir.glob(f"*{family}*"))
                if existing:
                    print(f"  Using existing files for {family}: {[f.name for f in existing]}")
                    downloaded.extend(existing)
        
        return downloaded
    
    def download_all(self) -> Dict[str, List[Path]]:
        """Download all STM32 family datasheets"""
        results = {}
        
        for family in self.family_datasheets.keys():
            results[family] = self.download_family(family)
        
        # Save manifest
        manifest = {
            "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "families": {
                family: [str(p) for p in paths]
                for family, paths in results.items()
            }
        }
        
        manifest_path = self.output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        
        total = sum(len(paths) for paths in results.values())
        print(f"\n{'='*60}")
        print(f"✓ Downloaded {total} datasheets")
        print(f"  Manifest: {manifest_path}")
        print(f"{'='*60}\n")
        
        return results


if __name__ == "__main__":
    downloader = STM32DatasheetDownloader()
    
    # Download all families
    results = downloader.download_all()
    
    # Summary
    print("\nSummary:")
    for family, paths in results.items():
        print(f"  {family}: {len(paths)} datasheets")
