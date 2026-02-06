"""
Celery Worker for Ingestion Pipeline

Background worker for processing datasheet ingestion tasks.
"""

import logging
import os
from celery import Celery
from celery.signals import worker_ready
import asyncio

from core.database import Database
from ingestion import (
    DocumentFetcher,
    PDFParser,
    FieldExtractor,
    Normalizer,
    Validator,
    Publisher,
)

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    'hardwaregenius',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3000,  # 50 minutes soft limit
)

# Global database connection
db = Database()


@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    """Initialize database connection when worker starts"""
    logger.info("Worker ready, initializing database connection")
    asyncio.run(db.connect())


@celery_app.task(name='ingest_document', bind=True)
def ingest_document(self, url: str, source_type: str = 'manufacturer_pdf'):
    """
    Ingest a single document (PDF or HTML).
    
    Args:
        url: Document URL
        source_type: Type of source (manufacturer_pdf, manufacturer_html, etc.)
    
    Returns:
        Dict with ingestion results
    """
    logger.info(f"Starting ingestion for: {url}")
    
    try:
        # Update task state
        self.update_state(state='PROGRESS', meta={'step': 'fetching', 'progress': 10})
        
        # Run async ingestion
        result = asyncio.run(_ingest_document_async(url, source_type, self))
        
        logger.info(f"Ingestion complete for: {url}")
        return result
    
    except Exception as e:
        logger.error(f"Ingestion failed for {url}: {e}", exc_info=True)
        raise


async def _ingest_document_async(url: str, source_type: str, task):
    """Async ingestion pipeline"""
    from uuid import uuid4
    
    run_id = uuid4()
    
    # Initialize components
    fetcher = DocumentFetcher(
        s3_endpoint=os.getenv('S3_ENDPOINT', 'http://localhost:9000'),
        s3_access_key=os.getenv('S3_ACCESS_KEY', 'minioadmin'),
        s3_secret_key=os.getenv('S3_SECRET_KEY', 'minioadmin123'),
        s3_bucket=os.getenv('S3_BUCKET_DOCUMENTS', 'documents'),
    )
    
    pdf_parser = PDFParser()
    extractor = FieldExtractor()
    normalizer = Normalizer()
    validator = Validator()
    publisher = Publisher(db.pool)
    
    # Step 1: Fetch document
    task.update_state(state='PROGRESS', meta={'step': 'fetching', 'progress': 20})
    logger.info(f"Fetching document: {url}")
    
    doc_record = await fetcher.fetch_and_store(url, source_type)
    
    if not doc_record:
        return {'status': 'error', 'message': 'Failed to fetch document'}
    
    # Step 2: Parse PDF
    task.update_state(state='PROGRESS', meta={'step': 'parsing', 'progress': 30})
    logger.info(f"Parsing PDF: {doc_record['storage_key']}")
    
    # Download from S3 to temp file
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp_path = tmp.name
        await fetcher.s3_client.fget_object(
            fetcher.s3_bucket,
            doc_record['storage_key'],
            tmp_path,
        )
    
    try:
        parsed_data = pdf_parser.parse(tmp_path)
    finally:
        os.unlink(tmp_path)
    
    # Step 3: Extract fields
    task.update_state(state='PROGRESS', meta={'step': 'extracting', 'progress': 50})
    logger.info("Extracting fields")
    
    extractions = extractor.extract_all_fields(
        parsed_data['text'],
        parsed_data['tables'],
    )
    
    # Step 4: Normalize
    task.update_state(state='PROGRESS', meta={'step': 'normalizing', 'progress': 60})
    logger.info("Normalizing values")
    
    normalized = {}
    for field_name, raw_value in extractions.items():
        normalized[field_name] = normalizer.normalize_field(field_name, raw_value)
    
    # Step 5: Validate
    task.update_state(state='PROGRESS', meta={'step': 'validating', 'progress': 70})
    logger.info("Validating data")
    
    validation_result = validator.validate_part_data(normalized)
    
    # Step 6: Publish
    task.update_state(state='PROGRESS', meta={'step': 'publishing', 'progress': 80})
    logger.info("Publishing to database")
    
    publish_result = await publisher.publish_part(
        part_data=normalized,
        document_id=doc_record['id'],
        evidence_data=extractions,  # Raw extractions with evidence
        validation_result=validation_result,
        run_id=run_id,
    )
    
    # Step 7: Complete
    task.update_state(state='PROGRESS', meta={'step': 'complete', 'progress': 100})
    
    return {
        'status': 'success',
        'run_id': str(run_id),
        'document_id': str(doc_record['id']),
        'part_id': str(publish_result['part_id']) if publish_result else None,
        'fields_extracted': len(extractions),
        'fields_published': len(publish_result.get('published_fields', [])) if publish_result else 0,
        'conflicts': len(validation_result.get('conflicts', [])),
    }


@celery_app.task(name='ingest_batch')
def ingest_batch(urls: list):
    """
    Ingest multiple documents in batch.
    
    Args:
        urls: List of document URLs
    
    Returns:
        List of ingestion results
    """
    logger.info(f"Starting batch ingestion of {len(urls)} documents")
    
    results = []
    for url in urls:
        try:
            result = ingest_document.delay(url)
            results.append({
                'url': url,
                'task_id': result.id,
            })
        except Exception as e:
            logger.error(f"Failed to queue {url}: {e}")
            results.append({
                'url': url,
                'error': str(e),
            })
    
    return results


if __name__ == '__main__':
    # Run worker
    celery_app.worker_main([
        'worker',
        '--loglevel=info',
        '--concurrency=2',
    ])
