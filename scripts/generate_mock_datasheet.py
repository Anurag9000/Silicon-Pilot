
import fitz  # PyMuPDF
from pathlib import Path

OUTPUT_DIR = Path("d:/Done,Toreview/HardwareGenius/datasheets")
OUTPUT_FILE = OUTPUT_DIR / "mock_stm32.pdf"

def generate_mock_datasheet():
    doc = fitz.open()
    
    # Page 1: Title
    page = doc.new_page()
    page.insert_text((100, 100), "STM32F405xx STM32F407xx Datasheet", fontsize=20)
    
    # Page 2: Pin definitions
    page = doc.new_page()
    page.insert_text((50, 50), "2. Pinouts and pin description", fontsize=14)
    # Match the case expected by extractor: "Pin definition"
    page.insert_text((50, 80), "Table 7. STM32F40x Pin definition and ball definitions", fontsize=12)
    
    # Draw a table with lines (req for pdfplumber default strategy)
    # x cols: 50 (Pin), 150 (Type), 200 (Alt), 350 (Add), 500 (End)
    # y rows: 100 (Header), 120 (Row1), 150 (Row2)...
    
    headers = ["Pin name", "Type", "Alternate functions", "Additional functions"]
    data = [
        ["PA0-WKUP", "I/O", "TIM2_CH1_ETR, TIM5_CH1", "ADC123_IN0"],
        ["PA1", "I/O", "TIM2_CH2, TIM5_CH2", "ADC123_IN1"],
        ["PA2", "I/O", "TIM2_CH3, TIM5_CH3", "ADC123_IN2"],
        ["PB12", "I/O", "SPI2_NSS, I2C2_SMBA", "OTG_HS_ID"],
    ]
    
    start_y = 100
    row_height = 30
    cols = [50, 150, 200, 350, 500]
    
    # Draw Header
    for i, h in enumerate(headers):
        page.draw_rect(fitz.Rect(cols[i], start_y, cols[i+1], start_y + row_height), color=(0,0,0))
        page.insert_text((cols[i]+5, start_y+15), h, fontsize=10)
        
    current_y = start_y + row_height
    
    # Draw Rows
    for row in data:
        row_h = row_height
        if len(row[2]) > 20: row_h = row_height * 2 # simple multiline simulation
        
        for i, cell in enumerate(row):
            page.draw_rect(fitz.Rect(cols[i], current_y, cols[i+1], current_y + row_h), color=(0,0,0))
            page.insert_text((cols[i]+5, current_y+15), cell, fontsize=9)
            
        current_y += row_h
        
    # Page 3: Electrical characteristics
    page = doc.new_page()
    page.insert_text((50, 50), "5.3. Operating conditions", fontsize=14)
    page.insert_text((50, 80), "Table 12. Current consumption in Run mode", fontsize=12)
    
    # Power Table
    headers = ["Mode", "Conditions", "Typ", "Max", "Unit"]
    data = [
        ["Run", "HSI, 16MHz", "550", "600", "uA"],
        ["Sleep", "HSI, 16MHz", "300", "400", "uA"],
        ["Stop", "All peripherals off", "10", "20", "uA"],
    ]
    
    start_y = 100
    row_height = 30
    cols = [50, 150, 300, 380, 450, 500]
    
    # Draw Header
    for i, h in enumerate(headers):
        page.draw_rect(fitz.Rect(cols[i], start_y, cols[i+1], start_y + row_height), color=(0,0,0))
        page.insert_text((cols[i]+5, start_y+15), h, fontsize=10)
        
    current_y = start_y + row_height
    
    # Draw Rows
    for row in data:
        for i, cell in enumerate(row):
            page.draw_rect(fitz.Rect(cols[i], current_y, cols[i+1], current_y + row_height), color=(0,0,0))
            page.insert_text((cols[i]+5, current_y+15), cell, fontsize=9)
        current_y += row_height
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT_FILE)
    print(f"Generated mock datasheet: {OUTPUT_FILE}")
