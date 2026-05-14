"""
Ingestion Script

Trigger ingestion of collected datasheets into the database.
"""

import logging
import os
import sys
import json
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from worker import ingest_document

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


async def ingest_from_manifest(manifest_path: str):
    """
    Ingest datasheets from manifest file.
    
    Args:
        manifest_path: Path to manifest.json
    """
    logger.info(f"Loading manifest: {manifest_path}")
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    datasheets = manifest['datasheets']
    logger.info(f"Found {len(datasheets)} datasheets to ingest")
    
    # Queue ingestion tasks
    tasks = []
    for ds in datasheets:
        url = ds['url']
        logger.info(f"Queuing: {url}")
        
        # Use Celery to queue the task
        task = ingest_document.delay(url, 'manufacturer_pdf')
        tasks.append({
            'url': url,
            'part_family': ds['part_family'],
            'task_id': task.id,
        })
    
    logger.info(f"Queued {len(tasks)} ingestion tasks")
    
    # Save task IDs
    tasks_file = Path(manifest_path).parent / 'ingestion_tasks.json'
    with open(tasks_file, 'w') as f:
        json.dump(tasks, f, indent=2)
    
    logger.info(f"Task IDs saved to: {tasks_file}")
    
    return tasks


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ingest STM32 datasheets')
    parser.add_argument(
        '--manifest',
        default='data/stm32_datasheets/manifest.json',
        help='Path to manifest.json',
    )
    
    args = parser.parse_args()
    
    if not Path(args.manifest).exists():
        logger.error(f"Manifest not found: {args.manifest}")
        logger.info("Run 'python scripts/collect_stm32_datasheets.py' first")
        sys.exit(1)
    
    # Ingest
    tasks = asyncio.run(ingest_from_manifest(args.manifest))
    
    print(f"\n Queued {len(tasks)} ingestion tasks")
    print(f" Monitor progress in Celery logs")
    print(f" Check database for ingested parts")


if __name__ == '__main__':
    main()
