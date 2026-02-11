"""
Master Component Ingestion Orchestrator

Runs all component ingesters in sequence:
1. PMICs
2. DC-DC Converters
3. LDOs
4. (Future: CAN Transceivers, Sensors, Memory)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.component_ingesters.pmic_ingester import PMICIngester
from ingestion.component_ingesters.dcdc_ingester import DCDCIngester
from ingestion.component_ingesters.ldo_ingester import LDOIngester


async def run_all_ingesters(db_url: str):
    """Run all component ingesters sequentially"""
    
    print("\n" + "="*80)
    print(" "*20 + "COMPONENT INGESTION MASTER SCRIPT")
    print("="*80 + "\n")
    
    # 1. PMICs
    print("\n[1/3] Starting PMIC Ingestion...")
    pmic_ingester = PMICIngester(db_url)
    await pmic_ingester.ingest_all()
    
    # 2. DC-DC Converters
    print("\n[2/3] Starting DC-DC Converter Ingestion...")
    dcdc_ingester = DCDCIngester(db_url)
    await dcdc_ingester.ingest_all()
    
    # 3. LDOs
    print("\n[3/3] Starting LDO Ingestion...")
    ldo_ingester = LDOIngester(db_url)
    await ldo_ingester.ingest_all()
    
    print("\n" + "="*80)
    print(" "*25 + "ALL INGESTION COMPLETE")
    print("="*80 + "\n")


async def main():
    import os
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")
    
    await run_all_ingesters(db_url)


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
