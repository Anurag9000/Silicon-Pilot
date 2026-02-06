"""
Document Fetcher

Downloads manufacturer datasheets and product pages with proper caching,
versioning, and rate limiting.
"""

import hashlib
import logging
import time
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import boto3
from botocore.client import Config
from datetime import datetime

from core.models import DocumentRecord, SourceType

logger = logging.getLogger(__name__)


class DocumentFetcher:
    """Fetch and cache documents with S3 storage"""
    
    def __init__(
        self,
        s3_endpoint: str,
        s3_access_key: str,
        s3_secret_key: str,
        s3_bucket: str,
        rate_limit_delay: float = 1.0,
    ):
        """
        Initialize document fetcher.
        
        Args:
            s3_endpoint: MinIO/S3 endpoint URL
            s3_access_key: S3 access key
            s3_secret_key: S3 secret key
            s3_bucket: Bucket name for documents
            rate_limit_delay: Minimum delay between requests (seconds)
        """
        self.s3_bucket = s3_bucket
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0.0
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            endpoint_url=s3_endpoint,
            aws_access_key_id=s3_access_key,
            aws_secret_access_key=s3_secret_key,
            config=Config(signature_version='s3v4'),
        )
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
        
        # Initialize HTTP session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # User agent for requests
        self.session.headers.update({
            'User-Agent': 'HardwareGenius/1.0 (Educational Project; +https://github.com/Anurag9000/HardwareGenius)'
        })
    
    def _ensure_bucket_exists(self):
        """Create S3 bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
            logger.info(f"S3 bucket '{self.s3_bucket}' exists")
        except Exception as e:
            # Bucket doesn't exist or access denied, try to create
            try:
                self.s3_client.create_bucket(Bucket=self.s3_bucket)
                logger.info(f"Created S3 bucket '{self.s3_bucket}'")
            except Exception as e:
                logger.error(f"Failed to create S3 bucket: {e}")
                raise
    
    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def _compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of content"""
        return hashlib.sha256(content).hexdigest()
    
    def _detect_source_type(self, url: str, content_type: str) -> SourceType:
        """Detect source type from URL and content type"""
        url_lower = url.lower()
        
        # Check for manufacturer domains
        manufacturer_domains = [
            'st.com', 'stmicroelectronics.com',
            'espressif.com',
            'nordicsemi.com',
            'microchip.com',
            'ti.com', 'texas instruments',
            'nxp.com',
            'infineon.com',
            'renesas.com',
        ]
        
        is_manufacturer = any(domain in url_lower for domain in manufacturer_domains)
        
        if 'pdf' in content_type.lower() or url_lower.endswith('.pdf'):
            return SourceType.MFG_PDF if is_manufacturer else SourceType.OTHER
        elif 'html' in content_type.lower():
            return SourceType.MFG_HTML if is_manufacturer else SourceType.OTHER
        else:
            return SourceType.OTHER
    
    def fetch(
        self,
        url: str,
        force_refetch: bool = False,
    ) -> Tuple[DocumentRecord, bytes]:
        """
        Fetch document from URL and store in S3.
        
        Args:
            url: URL to fetch
            force_refetch: Force re-download even if cached
        
        Returns:
            Tuple of (DocumentRecord, content_bytes)
        """
        logger.info(f"Fetching document: {url}")
        
        # Rate limit
        self._rate_limit()
        
        # Fetch content
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            content = response.content
            content_type = response.headers.get('Content-Type', 'application/octet-stream')
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise
        
        # Compute hash
        doc_hash = self._compute_hash(content)
        
        # Generate storage key
        parsed_url = urlparse(url)
        filename = Path(parsed_url.path).name or 'document'
        storage_key = f"documents/{doc_hash[:8]}/{filename}"
        
        # Check if already exists in S3
        if not force_refetch:
            try:
                self.s3_client.head_object(Bucket=self.s3_bucket, Key=storage_key)
                logger.info(f"Document already exists in S3: {storage_key}")
            except Exception:
                pass  # Doesn't exist, will upload
        
        # Upload to S3
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=storage_key,
                Body=content,
                ContentType=content_type,
                Metadata={
                    'source_url': url,
                    'doc_hash': doc_hash,
                    'fetched_at': datetime.utcnow().isoformat(),
                }
            )
            logger.info(f"Uploaded document to S3: {storage_key}")
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise
        
        # Detect source type
        source_type = self._detect_source_type(url, content_type)
        
        # Create document record
        doc_record = DocumentRecord(
            source_url=url,
            source_type=source_type,
            doc_hash=doc_hash,
            content_type=content_type,
            storage_key=storage_key,
            fetched_at=datetime.utcnow(),
        )
        
        return doc_record, content
    
    def get_from_s3(self, storage_key: str) -> bytes:
        """Retrieve document from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=storage_key
            )
            return response['Body'].read()
        except Exception as e:
            logger.error(f"Failed to retrieve from S3: {e}")
            raise
