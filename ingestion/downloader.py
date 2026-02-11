
import os
import requests
import time
from pathlib import Path
import logging
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class DatasheetDownloader:
    def __init__(self, download_dir: str = "datasheets"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Configure robust session
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1, # 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def download(self, url: str, filename: str) -> str:
        """
        Downloads a file from URL. Returns the local path.
        Skips if already exists.
        """
        if not url:
            return None
            
        local_path = self.download_dir / filename
        if local_path.exists() and local_path.stat().st_size > 1024:
            # logger.info(f"File {filename} already exists. Skipping download.")
            return str(local_path)
            
        logger.info(f"Downloading {url} to {local_path}...")
        try:
            # Stream download
            with self.session.get(url, stream=True, timeout=30) as response:
                response.raise_for_status()
                
                # Content-Type Check (ST sometimes redirects pdf->html on 404 soft landing)
                content_type = response.headers.get('Content-Type', '').lower()
                if 'html' in content_type:
                    logger.warning(f"  ⚠️ URL returned HTML instead of file (Content-Type: {content_type}). Skipping.")
                    return None
                
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            # Size check
            if local_path.stat().st_size < 1000:
                logger.warning(f"  ⚠️ Downloaded file {filename} is too small (<1KB). Deleting.")
                local_path.unlink()
                return None
                
            return str(local_path)
            
        except Exception as e:
            logger.error(f"  ❌ Failed to download {url}: {e}")
            if local_path.exists():
                local_path.unlink()
            return None
