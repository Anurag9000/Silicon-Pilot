# HardwareGenius: Ingestion & Extraction Tuning Guide

In HardwareGenius, "training" refers to the process of tuning the ingestion pipeline to correctly identify, extract, and normalize specifications from manufacturer documents.

---

## 1. Tuning Extraction Patterns

The `FieldExtractor` uses regular expressions to find specifications in text blocks.

**File:** `ingestion/extractor.py`

### Adding New Peripheral Patterns
To add a new peripheral (e.g., "Ethernet"):
1. Open `ingestion/extractor.py`.
2. Find the `_init_field_patterns` method.
3. Add a new entry:
   ```python
   'ethernet': [
       {'pattern': r'Ethernet\s+MAC', 'unit_multiplier': None},
       {'pattern': r'10/100\s+Ethernet', 'unit_multiplier': None},
   ]
   ```

---

## 2. Tuning Normalization Rules

The `Normalizer` standardizes raw strings into canonical values.

**File:** `ingestion/normalizer.py`

### Adding Peripheral Synonyms
If "M_CAN" should be treated as "CAN_FD":
1. Open `ingestion/normalizer.py`.
2. Add to `self.synonym_map['peripherals']`:
   ```python
   'M_CAN': 'CAN_FD'
   ```

### Custom Part Suffix Decoders
Each manufacturer has a code (e.g., `STM32F405RGT6`).
The `Normalizer` decodes these in `_decode_stm32_suffix`, `_decode_esp32_suffix`, etc.
To add a new vendor, implement a `_decode_[vendor]_suffix` method and call it in `decode_part_number`.

---

## 3. Tuning Table Extraction

Some tables are better parsed using `lattice` (good for borders) and others with `stream` (good for borderless).

**File:** `ingestion/pdf_parser.py`

Modify `@_extract_tables`:
- Adjust the `flavor` parameter.
- Add `table_areas` or `columns` hints if a specific datasheet is consistently failing.

---

## 4. Confidence Thresholds

You can tune how aggressive the system is in accepting data without human review.

**File:** `ingestion/publisher.py`

Modify `CONFIDENCE_THRESHOLD`:
- `0.95`: Very conservative, requires human review for almost everything.
- `0.70`: More automated, but higher risk of incorrect data.

---

## 5. Iterative Refinement Workflow

1. **Ingest**: Run `python scripts/ingest_datasheets.py`.
2. **Audit**: Check for conflicts in `GET /admin/conflicts`.
3. **Trace**: Use `GET /evidence/{id}` to see if the extraction bbox covers the right text.
4. **Fix**: Update regex/normalizer logic.
5. **Re-publish**: Re-run ingestion. The system uses UPSERT logic to update records.
