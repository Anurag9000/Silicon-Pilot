"""
Integration Test for Real Ingestion Logic (Mocking DB)
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path
import sys
import os

# Add root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ingestion.batch_ingestion import STM32Ingester, IngestionManager

@pytest.mark.asyncio
async def test_stm32_ingester_flow():
    """Test that PDF parsing flows into DB calls correctly"""
    
    # Mock data directory
    with patch('ingestion.batch_ingestion.Path') as MockPath:
        # File found
        mock_pdf = MagicMock()
        mock_pdf.name = "STM32F405_datasheet.pdf"
        mock_pdf.stem = "STM32F405_datasheet"
        mock_pdf.glob.return_value = [mock_pdf]
        
        # Mock dependencies
        with patch('ingestion.batch_ingestion.PDFParser') as MockParser, \
             patch('ingestion.batch_ingestion.FieldExtractor') as MockExtractor, \
             patch('ingestion.batch_ingestion.get_pool') as mock_get_pool:
            
            # Setup Parser return
            parser_instance = MockParser.return_value
            parser_instance.parse.return_value = {
                'pages': [
                    {'page_number': 1, 'text': 'STM32F405xx datasheet intro'},
                    {'page_number': 2, 'text': 'Flash memory 1024 KB'}
                ]
            }
            
            # Setup Extractor return
            extractor_instance = MockExtractor.return_value
            # MPN extraction
            extractor_instance.extract_mpns.return_value = ['STM32F405RG']
            # Field extraction
            extractor_instance.extract_field.side_effect = lambda field, text, page: {
                'field_name': field,
                'normalized_value': 1024 if field == 'flash_kb' else 0,
                'raw_value': '1024 KB',
                'page': page
            } if field == 'flash_kb' else None

            # Setup DB Mock
            mock_pool = MagicMock() # Pool object itself is not awaited, but its methods are
            mock_conn = AsyncMock() # Connection methods are async
            
            # pool.acquire() returns an async context manager, not a coroutine
            mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
            
            mock_get_pool.return_value = mock_pool
            
            # Run Ingestion
            ingester = STM32Ingester(data_dir="mock_data_dir")
            # Force listing of files since we mocked Path
            ingester.data_dir.glob = MagicMock(return_value=[mock_pdf])
            ingester.data_dir.exists.return_value = True
            
            count = await ingester.ingest_all_pdfs()
            
            # Assertions
            assert count == 1
            parser_instance.parse.assert_called_once()
            extractor_instance.extract_mpns.assert_called_once()
            # Check DB calls
            assert mock_conn.fetchrow.called # Document insert
            assert mock_conn.fetchval.called # Part insert
            assert mock_conn.execute.called # Spec/Evidence insert

if __name__ == "__main__":
    # Manually run the async test function if run as script
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_stm32_ingester_flow())
    print("Test passed!")
