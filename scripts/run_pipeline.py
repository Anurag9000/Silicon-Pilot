
"""
Master Ingestion Pipeline

Executes the entire Silicon-Pilot data ingestion flow in the correct order.
One command to rule them all.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Pipeline")

ROOT_DIR = Path(__file__).parent.parent
PYTHON_EXE = sys.executable

def run_script(script_path, desc):
    logger.info(f"\n{'='*60}\nSTEP: {desc}\n{'='*60}")
    full_path = ROOT_DIR / script_path
    
    if not full_path.exists():
        logger.error(f"Script not found: {full_path}")
        return False
        
    try:
        # Run synchronous
        result = subprocess.run(
            [PYTHON_EXE, str(full_path)], 
            cwd=str(ROOT_DIR),
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f" Step failed: {desc}")
        return False

def main():
    logger.info("Starting Silicon-Pilot Ingestion Pipeline...")
    
    # 1. Database Setup (Idempotent)
    if not run_script("scripts/setup_database.py", "Database Schema Setup"):
        return

    # 2. STM32 Ingestion (Seed Parts + Specs)
    if not run_script("ingestion/stm32_mcu_ingester.py", "STM32 Part Seeding"):
        return

    # 3. LDO Ingestion (Seed LDOs)
    if not run_script("ingestion/st_ldo_ingester.py", "LDO Part Seeding"):
        return

    # 3b. DC-DC Ingestion (Seed DC-DC)
    if not run_script("ingestion/st_dcdc_ingester.py", "DC-DC Part Seeding"):
        return

    # 3c. PMIC Ingestion (Seed PMIC)
    if not run_script("ingestion/st_pmic_ingester.py", "PMIC Part Seeding"):
        return

    # 3d. CAN Ingestion (Seed CAN)
    if not run_script("ingestion/st_can_ingester.py", "CAN Transceiver Seeding"):
        return

    # 3e. Sensor Ingestion (Seed Sensors)
    if not run_script("ingestion/st_sensor_ingester.py", "Sensor Part Seeding"):
        return

    # 3f. Passive Ingestion (Seed Resistors/Caps)
    if not run_script("ingestion/st_passive_ingester.py", "Passive Part Seeding"):
        return

    # 4. Full PDF Extraction (Download + Parse Details)
    # Note: This takes a long time. We'll run a limited batch by default for demonstration.
    if not run_script("ingestion/run_full_ingestion.py", "Datasheet Extraction (Batch)"):
        return

    # 5. Errata Ingestion (Download + Parse)
    if not run_script("ingestion/stm32_errata_ingester.py", "Errata Sheet Download"):
        return
        
    # 6. Errata Processing
    if not run_script("ingestion/run_errata_processing.py", "Errata Extraction"):
        return
        
    logger.info("\n Pipeline Completed Successfully!")

if __name__ == "__main__":
    main()
