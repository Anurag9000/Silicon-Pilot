
import time
import logging
from pathlib import Path
from ingestion.pdf_parser import PDFParser

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_optimization():
    parser = PDFParser()
    pdf_path = Path("data/pmic_datasheets/TPS65217_datasheet.pdf")
    
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found.")
        return

    print(f"Starting parse of {pdf_path}...")
    start_time = time.time()
    
    result = parser.parse(str(pdf_path))
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\nParsing complete in {duration:.2f} seconds.")
    print(f"Total Pages: {len(result['pages'])}")
    print(f"Extracted Tables: {len(result['tables'])}")
    
    # Check if table extraction was targeted
    # We can infer this from logs, but here we just check speed and result
    if duration < 60:
        print("SUCCESS: Parsing took less than 60 seconds.")
    else:
        print("WARNING: Parsing took longer than 60 seconds.")

if __name__ == "__main__":
    test_optimization()
