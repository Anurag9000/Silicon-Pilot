"""
Quick Test Script

Test the system without Docker (for development).
"""

import asyncio
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


async def test_ingestion_components():
    """Test ingestion components without database"""
    from ingestion import PDFParser, FieldExtractor, Normalizer, Validator
    
    logger.info("Testing ingestion components")
    
    # Find a downloaded datasheet
    datasheet_dir = Path("data/stm32_datasheets")
    pdfs = list(datasheet_dir.glob("*.pdf"))
    
    if not pdfs:
        logger.error("No PDFs found. Run collect_stm32_datasheets.py first")
        return
    
    test_pdf = pdfs[0]
    logger.info(f"Testing with: {test_pdf}")
    
    # Step 1: Parse PDF
    logger.info("Step 1: Parsing PDF...")
    parser = PDFParser()
    parsed_data = parser.parse(str(test_pdf))
    
    # Combine text from all pages
    full_text = "\n".join([page['text'] for page in parsed_data['pages']])
    
    logger.info(f"  - Extracted {len(full_text)} characters of text")
    logger.info(f"  - Found {len(parsed_data['tables'])} tables")
    logger.info(f"  - Processed {len(parsed_data['pages'])} pages")
    
    # Step 2: Extract fields
    logger.info("Step 2: Extracting fields...")
    extractor = FieldExtractor()
    extractions = extractor.extract_all_fields(
        full_text,
        parsed_data['tables'],
    )
    
    logger.info(f"  - Extracted {len(extractions)} fields:")
    for field_name, value in list(extractions.items())[:10]:
        logger.info(f"    • {field_name}: {value}")
    
    # Step 3: Normalize
    logger.info("Step 3: Normalizing values...")
    normalizer = Normalizer()
    normalized = {}
    for field_name, raw_value in extractions.items():
        normalized[field_name] = normalizer.normalize_field(field_name, raw_value)
    
    logger.info(f"  - Normalized {len(normalized)} fields")
    
    # Step 4: Validate
    logger.info("Step 4: Validating data...")
    validator = Validator()
    validation_result = validator.validate_part_data(normalized)
    
    logger.info(f"  - Valid: {validation_result['is_valid']}")
    logger.info(f"  - Errors: {len(validation_result.get('errors', []))}")
    logger.info(f"  - Warnings: {len(validation_result.get('warnings', []))}")
    logger.info(f"  - Confidence: {validation_result.get('confidence', 0):.2f}")
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("✅ Ingestion pipeline test complete!")
    logger.info(f"📄 Tested: {test_pdf.name}")
    logger.info(f"📊 Extracted: {len(extractions)} fields")
    logger.info(f"✓ Validation: {'PASS' if validation_result['is_valid'] else 'FAIL'}")
    logger.info("="*60)
    
    return {
        'pdf': str(test_pdf),
        'extractions': extractions,
        'normalized': normalized,
        'validation': validation_result,
    }


async def test_solver_components():
    """Test solver components"""
    from core.models import RequirementSpec, OptimizationGoal
    from solver import RankingEngine
    
    logger.info("\nTesting solver components")
    
    # Create test spec
    spec = RequirementSpec(
        hard_constraints={
            'flash_kb': {'min': 512},
            'sram_kb': {'min': 128},
        },
        optimization_goal=OptimizationGoal.BALANCED,
    )
    
    # Create test candidates
    candidates = [
        {
            'mpn': 'STM32F405RGT6',
            'manufacturer': 'STMicroelectronics',
            'family': 'STM32F4',
            'flash_kb': 1024,
            'sram_kb': 192,
            'can_count': 2,
            'max_mhz': 168,
            'has_fpu': True,
            'status': 'active',
            'cost_usd': 5.50,
        },
        {
            'mpn': 'STM32F407VGT6',
            'manufacturer': 'STMicroelectronics',
            'family': 'STM32F4',
            'flash_kb': 1024,
            'sram_kb': 192,
            'can_count': 2,
            'max_mhz': 168,
            'has_fpu': True,
            'status': 'active',
            'cost_usd': 6.00,
        },
    ]
    
    # Test ranking
    logger.info("Testing ranking engine...")
    ranking_engine = RankingEngine()
    ranked = ranking_engine.rank(candidates, spec)
    
    logger.info(f"  - Ranked {len(ranked)} candidates")
    for i, (candidate, score, breakdown) in enumerate(ranked, 1):
        logger.info(f"  {i}. {candidate['mpn']}: {score:.3f}")
        logger.info(f"     Breakdown: {breakdown}")
    
    logger.info("\n✅ Solver test complete!")
    
    return ranked


async def main():
    """Main test runner"""
    logger.info("="*60)
    logger.info("HardwareGenius Quick Test")
    logger.info("="*60)
    
    try:
        # Test ingestion
        ingestion_result = await test_ingestion_components()
        
        # Test solver
        solver_result = await test_solver_components()
        
        logger.info("\n" + "="*60)
        logger.info("🎉 ALL TESTS PASSED!")
        logger.info("="*60)
        logger.info("\nNext steps:")
        logger.info("1. Start Docker services: docker-compose up -d")
        logger.info("2. Apply schema: docker-compose exec postgres psql ...")
        logger.info("3. Run full ingestion: python scripts/ingest_datasheets.py")
        logger.info("4. Test API: http://localhost:8000/docs")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == '__main__':
    exit(asyncio.run(main()))
