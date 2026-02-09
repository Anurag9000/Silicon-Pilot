# STM32 Documentation Download Guide

## 🎯 Comprehensive STM32 Documentation Collection

This guide covers downloading **ALL** STM32 family documentation from official ST sources.

---

## 📦 What's Being Downloaded

### **Document Types**
1. **Datasheets (DS)** - Electrical specs, pinouts, packages
2. **Reference Manuals (RM)** - Detailed peripheral descriptions
3. **Programming Manuals (PM)** - Core programming details
4. **Errata Sheets (ES)** - Silicon bugs and workarounds
5. **Application Notes (AN)** - Design guidelines

### **STM32 Families Covered (20 families)**

#### Mainstream (Cortex-M0/M0+/M3/M4/M7)
- **STM32F0** - Entry-level Cortex-M0
- **STM32F1** - Mainstream Cortex-M3
- **STM32F2** - High-performance Cortex-M3
- **STM32F3** - Mixed-signal Cortex-M4
- **STM32F4** - High-performance Cortex-M4
- **STM32F7** - Very high-performance Cortex-M7

#### High-Performance
- **STM32H7** - Dual-core Cortex-M7 (480 MHz)
- **STM32H5** - Cortex-M33 with security

#### Ultra-Low-Power
- **STM32L0** - Ultra-low-power Cortex-M0+
- **STM32L1** - Ultra-low-power Cortex-M3
- **STM32L4** - Ultra-low-power Cortex-M4
- **STM32L4+** - Enhanced L4 series
- **STM32L5** - Secure ultra-low-power Cortex-M33
- **STM32U5** - Next-gen ultra-low-power Cortex-M33

#### Value Line
- **STM32C0** - Cost-optimized Cortex-M0+
- **STM32G0** - Mainstream value Cortex-M0+
- **STM32G4** - Mixed-signal Cortex-M4

#### Wireless
- **STM32WB** - Dual-core BLE/802.15.4
- **STM32WBA** - Next-gen wireless
- **STM32WL** - Sub-GHz wireless LoRa

---

## 🔗 Official ST.com Links

### Main Portal
```
https://www.st.com/en/microcontrollers-microprocessors/stm32-32-bit-arm-cortex-mcus.html
```

### Parametric Search (Best for discovery)
```
https://www.st.com/en/microcontrollers-microprocessors/stm32-32-bit-arm-cortex-mcus.html#products
```

### Family-Specific Pages

| Family | URL |
|--------|-----|
| STM32F0 | https://www.st.com/en/microcontrollers-microprocessors/stm32f0-series.html |
| STM32F1 | https://www.st.com/en/microcontrollers-microprocessors/stm32f1-series.html |
| STM32F2 | https://www.st.com/en/microcontrollers-microprocessors/stm32f2-series.html |
| STM32F3 | https://www.st.com/en/microcontrollers-microprocessors/stm32f3-series.html |
| STM32F4 | https://www.st.com/en/microcontrollers-microprocessors/stm32f4-series.html |
| STM32F7 | https://www.st.com/en/microcontrollers-microprocessors/stm32f7-series.html |
| STM32H7 | https://www.st.com/en/microcontrollers-microprocessors/stm32h7-series.html |
| STM32H5 | https://www.st.com/en/microcontrollers-microprocessors/stm32h5-series.html |
| STM32L0 | https://www.st.com/en/microcontrollers-microprocessors/stm32l0-series.html |
| STM32L1 | https://www.st.com/en/microcontrollers-microprocessors/stm32l1-series.html |
| STM32L4 | https://www.st.com/en/microcontrollers-microprocessors/stm32l4-series.html |
| STM32L4+ | https://www.st.com/en/microcontrollers-microprocessors/stm32l4-plus-series.html |
| STM32L5 | https://www.st.com/en/microcontrollers-microprocessors/stm32l5-series.html |
| STM32U5 | https://www.st.com/en/microcontrollers-microprocessors/stm32u5-series.html |
| STM32C0 | https://www.st.com/en/microcontrollers-microprocessors/stm32c0-series.html |
| STM32G0 | https://www.st.com/en/microcontrollers-microprocessors/stm32g0-series.html |
| STM32G4 | https://www.st.com/en/microcontrollers-microprocessors/stm32g4-series.html |
| STM32WB | https://www.st.com/en/microcontrollers-microprocessors/stm32wb-series.html |
| STM32WBA | https://www.st.com/en/microcontrollers-microprocessors/stm32wba-series.html |
| STM32WL | https://www.st.com/en/microcontrollers-microprocessors/stm32wl-series.html |

---

## 🚀 Running the Downloader

### Automated Download Script
```bash
python scripts/download_all_stm32_docs.py
```

### What It Does
1. ✅ Crawls all 20 STM32 family pages
2. ✅ Extracts all product links
3. ✅ Downloads datasheets, reference manuals, errata, etc.
4. ✅ Organizes by family and document type
5. ✅ Respects rate limits (2s delay)
6. ✅ Retries failed downloads
7. ✅ Logs all downloads

### Output Structure
```
data/stm32_documentation/
├── STM32F0/
│   ├── STM32F030/
│   │   ├── datasheet/
│   │   ├── reference_manual/
│   │   ├── errata/
│   │   └── application_note/
│   └── STM32F051/
├── STM32F1/
├── STM32F4/
├── STM32H7/
├── STM32L4/
├── STM32WB/
└── download_log.json
```

---

## 📊 Expected Results

### Estimated Download
- **Families**: 20
- **Products per family**: 10-50
- **Documents per product**: 3-10
- **Total files**: ~2,000-5,000 PDFs
- **Total size**: ~10-30 GB
- **Time**: 4-12 hours (with 2s delay)

---

## ⚙️ Configuration

Edit `scripts/download_all_stm32_docs.py` to customize:

```python
# Adjust delay (be respectful to ST servers)
DELAY_BETWEEN_REQUESTS = 2.0  # seconds

# Change output directory
OUTPUT_DIR = Path("data/stm32_documentation")

# Filter document types
DOCUMENT_TYPES = {
    "datasheet": ["DS", "datasheet"],
    "reference_manual": ["RM", "reference manual"],
    # Add or remove types as needed
}
```

---

## 🔍 Manual Download Links

If you need specific families only:

### STM32F4 (Most Popular)
- Product page: https://www.st.com/en/microcontrollers-microprocessors/stm32f4-series.html
- Direct documentation: Click "Documentation" tab on product pages

### STM32H7 (High Performance)
- Product page: https://www.st.com/en/microcontrollers-microprocessors/stm32h7-series.html

### STM32L4 (Ultra-Low-Power)
- Product page: https://www.st.com/en/microcontrollers-microprocessors/stm32l4-series.html

### STM32WB (Wireless)
- Product page: https://www.st.com/en/microcontrollers-microprocessors/stm32wb-series.html

---

## 📝 Notes

- **Rate Limiting**: Script uses 2-second delays to be respectful
- **Retries**: Automatic retry on failures (3 attempts)
- **Resume**: Re-running skips already downloaded files
- **Logging**: All downloads logged to `download_log.json`

---

## 🎯 Next Steps

After download completes:
1. Review `data/stm32_documentation/download_log.json`
2. Ingest into HardwareGenius database
3. Run extraction and normalization pipeline
4. Validate data quality

---

**Status**: ✅ Script running - check terminal for progress
