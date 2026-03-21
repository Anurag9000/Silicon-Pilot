"""
Deep STM32 Datasheet Parameter Extractor
=========================================

Extracts ALL major parameter sections from STM32 datasheets using pdfplumber.

Sections targeted:
  1. Absolute Maximum Ratings
  2. DC Electrical Characteristics (Vih, Vil, Voh, Vol, Icc, leakage)
  3. AC Timing Characteristics (SPI clk, I2C speed, CAN bitrate)
  4. Current Consumption (Run, Sleep, Stop1/2, Standby, VBAT modes)
  5. GPIO / I/O Characteristics (sink/source, 5V tolerance)
  6. Clock / PLL Specs (RC accuracy, PLL VCO, LSE)
  7. Thermal Characteristics (θJA, θJC per package)
  8. Features Summary (parsed bullet list from cover page)

Returns a list of parameter dicts each containing:
  {section, parameter, min_value, typ_value, max_value, unit, conditions, source_page, raw_text, confidence}
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Section keyword triggers (text that marks the START of each section in a PDF)
# ──────────────────────────────────────────────────────────────────────────────

SECTION_KEYWORDS = {
    "absolute_max": [
        "absolute maximum ratings",
        "maximum rated conditions",
    ],
    "dc_characteristics": [
        "general operating conditions",
        "dc characteristics",
        "electrical characteristics",
        "operating supply voltage",
        "input/output current capability",
    ],
    "ac_timing": [
        "ac characteristics",
        "timing characteristics",
        "spi characteristics",
        "i2c characteristics",
        "uart characteristics",
        "can characteristics",
        "slave characteristics",
        "master characteristics",
    ],
    "current_consumption": [
        "current consumption",
        "supply current",
        "typical current",
        "dynamic current",
    ],
    "gpio_io": [
        "i/o port characteristics",
        "io port characteristics",
        "gpio characteristics",
        "output driving current",
        "5 v tolerant",
    ],
    "clock_specs": [
        "internal rc oscillator",
        "hsi clock",
        "lsi oscillator",
        "pll characteristics",
        "oscillator characteristics",
    ],
    "thermal": [
        "thermal characteristics",
        "junction temperature",
        "thermal resistance",
        r"θja",
        r"r\s*th\s*ja",
    ],
    "features": [
        "features",
        "key features",
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# Patterns for extracting individual parameter rows
# Units are loosely matched
# ──────────────────────────────────────────────────────────────────────────────

# Matches a line like:  "VIH   Input high voltage   0.7 VDD  –  VDD + 0.4  V"
PARAM_LINE_PATTERN = re.compile(
    r"(?P<symbol>[A-Za-zα-ωΑ-Ω_()\[\]/][^\t\n]{1,60}?)"
    r"\s{2,}"
    r"(?P<values>[\d\.,\-–+\s]+(?:mA|µA|uA|mV|V|MHz|kHz|Hz|°C|C|Ω|ns|ps|pF|ms|%|dBm))"
    r"\s*$",
    re.MULTILINE,
)

# Matches a 3-column min/typ/max row (whitespace separated numbers)
MIN_TYP_MAX_PATTERN = re.compile(
    r"(?P<min>-{0,1}\d+\.?\d*|-)\s+(?P<typ>-{0,1}\d+\.?\d*|-)\s+(?P<max>-{0,1}\d+\.?\d*|-)\s+(?P<unit>\S+)",
)

# Theta_JA extraction
THETA_JA_PATTERN = re.compile(
    r"(?:θ\s*JA|Theta\s*JA|R\s*th\s*JA)[^\d]*([\d\.]+)\s*(°C/W|K/W)",
    re.IGNORECASE,
)

THETA_JC_PATTERN = re.compile(
    r"(?:θ\s*JC|Theta\s*JC|R\s*th\s*JC)[^\d]*([\d\.]+)\s*(°C/W|K/W)",
    re.IGNORECASE,
)

# Features bullet: "2 × 12-bit ADC, 2 Msps"
FEATURE_BULLET_PATTERN = re.compile(
    r"[•\-–▪]\s*(.{5,120})",
    re.MULTILINE,
)


class DeepDatasheetExtractor:
    """
    Extracts ALL major parameter categories from STM32 datasheets (and similar MCU PDFs).
    """

    def __init__(self, pdf_path: str, mpn: str = ""):
        self.pdf_path = pdf_path
        self.mpn = mpn
        self._pages: Optional[List[Any]] = None  # lazy-loaded

    # ──────────────────────────────────────────────────────────────────────────
    # Public entry point
    # ──────────────────────────────────────────────────────────────────────────

    def extract_all(self) -> List[Dict[str, Any]]:
        """
        Main entry: opens the PDF, scans every page, and returns a flat list of extracted parameters.
        """
        try:
            import pdfplumber
        except ImportError:
            logger.warning("pdfplumber not installed — skipping PDF extraction")
            return []

        results: List[Dict[str, Any]] = []

        with pdfplumber.open(self.pdf_path) as pdf:
            self._pages = pdf.pages
            total = len(pdf.pages)
            logger.info(f"Extracting '{self.mpn}' from {total}-page PDF: {self.pdf_path}")

            for page_idx, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                text_lower = text.lower()

                # ── Features (cover first 4 pages) ──
                if page_idx < 4:
                    results.extend(self._extract_features(text, page_idx + 1))

                # ── Detect section and parse accordingly ──
                section = self._detect_section(text_lower)

                if section == "absolute_max":
                    results.extend(self._extract_table_rows(page, text, "absolute_max", page_idx + 1))

                elif section == "dc_characteristics":
                    results.extend(self._extract_table_rows(page, text, "dc_characteristics", page_idx + 1))

                elif section == "ac_timing":
                    results.extend(self._extract_table_rows(page, text, "ac_timing", page_idx + 1))

                elif section == "current_consumption":
                    results.extend(self._extract_current_consumption(page, text, page_idx + 1))

                elif section == "gpio_io":
                    results.extend(self._extract_table_rows(page, text, "gpio_io", page_idx + 1))

                elif section == "clock_specs":
                    results.extend(self._extract_table_rows(page, text, "clock_specs", page_idx + 1))

                elif section == "thermal":
                    results.extend(self._extract_thermal(text, page_idx + 1))

        # Deduplicate by (section, parameter) keeping highest confidence
        deduped = {}
        for row in results:
            key = (row["section"], row["parameter"])
            if key not in deduped or row.get("confidence", 0) > deduped[key].get("confidence", 0):
                deduped[key] = row

        return list(deduped.values())

    # ──────────────────────────────────────────────────────────────────────────
    # Section detection
    # ──────────────────────────────────────────────────────────────────────────

    def _detect_section(self, text_lower: str) -> Optional[str]:
        for section, keywords in SECTION_KEYWORDS.items():
            for kw in keywords:
                if re.search(kw, text_lower):
                    return section
        return None

    # ──────────────────────────────────────────────────────────────────────────
    # Table-based extraction (generic for DC, AC, Absolute Max, GPIO, Clock)
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_table_rows(
        self, page, text: str, section: str, page_num: int
    ) -> List[Dict[str, Any]]:
        results = []

        # Method 1: pdfplumber table extraction
        try:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue
                rows = self._parse_min_typ_max_table(table, section, page_num)
                results.extend(rows)
        except Exception as e:
            logger.debug(f"Table extraction failed page {page_num}: {e}")

        # Method 2: text line regex fallback
        if not results:
            results.extend(self._extract_line_params(text, section, page_num))

        return results

    def _parse_min_typ_max_table(
        self, table: List[List], section: str, page_num: int
    ) -> List[Dict[str, Any]]:
        """
        Attempts to parse a table that has Parameter | Description | Min | Typ | Max | Unit columns.
        """
        results = []
        if not table or not table[0]:
            return results

        headers = [str(h or "").lower().strip() for h in table[0]]

        # Identify column indices
        param_col = self._find_col(headers, ["symbol", "parameter", "param", "name"])
        desc_col  = self._find_col(headers, ["description", "condition", "test condition"])
        min_col   = self._find_col(headers, ["min"])
        typ_col   = self._find_col(headers, ["typ"])
        max_col   = self._find_col(headers, ["max"])
        unit_col  = self._find_col(headers, ["unit", "mhz", "v", "ma"])

        if param_col == -1 and min_col == -1:
            return results  # Not a parameter table

        for row in table[1:]:
            try:
                if not row or all(c is None or str(c).strip() == "" for c in row):
                    continue

                # Get parameter name
                param = ""
                if param_col != -1 and param_col < len(row):
                    param = str(row[param_col] or "").replace("\n", " ").strip()
                if not param:
                    continue

                # Get values
                def safe(col: int) -> str:
                    if col == -1 or col >= len(row):
                        return "-"
                    val = str(row[col] or "").strip()
                    return val if val else "-"

                results.append({
                    "section": section,
                    "parameter": param,
                    "min_value": safe(min_col),
                    "typ_value": safe(typ_col),
                    "max_value": safe(max_col),
                    "unit": safe(unit_col),
                    "conditions": safe(desc_col),
                    "source_page": page_num,
                    "raw_text": " | ".join(str(c or "") for c in row),
                    "confidence": 0.85,
                })
            except Exception:
                continue

        return results

    def _find_col(self, headers: List[str], candidates: List[str]) -> int:
        for i, h in enumerate(headers):
            for c in candidates:
                if c in h:
                    return i
        return -1

    def _extract_line_params(
        self, text: str, section: str, page_num: int
    ) -> List[Dict[str, Any]]:
        """Regex-based line extraction fallback."""
        results = []
        for m in PARAM_LINE_PATTERN.finditer(text):
            symbol = m.group("symbol").strip()
            raw_val = m.group("values").strip()
            unit_match = re.search(r"(mA|µA|uA|mV|V|MHz|kHz|Hz|°C|C|Ω|ns|ps|pF|ms|%|dBm)", raw_val)
            unit = unit_match.group(1) if unit_match else ""
            results.append({
                "section": section,
                "parameter": symbol,
                "min_value": "-",
                "typ_value": raw_val,
                "max_value": "-",
                "unit": unit,
                "conditions": "",
                "source_page": page_num,
                "raw_text": m.group(0).strip(),
                "confidence": 0.6,
            })
        return results

    # ──────────────────────────────────────────────────────────────────────────
    # Current Consumption (separate because often uses very specific tables)
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_current_consumption(
        self, page, text: str, page_num: int
    ) -> List[Dict[str, Any]]:
        results = []
        try:
            tables = page.extract_tables()
            for table in tables:
                rows = self._parse_min_typ_max_table(table, "current_consumption", page_num)
                results.extend(rows)
        except Exception:
            pass

        # Regex fallback: look for mA/µA amounts in run/sleep/stop lines
        current_patterns = [
            (r"Run\s+mode[^\n]*?([\d\.]+)\s*(mA|µA|uA)", "Run mode current"),
            (r"Sleep\s+mode[^\n]*?([\d\.]+)\s*(mA|µA|uA)", "Sleep mode current"),
            (r"Stop\s+1[^\n]*?([\d\.]+)\s*(mA|µA|uA)", "Stop1 mode current"),
            (r"Stop\s+2[^\n]*?([\d\.]+)\s*(mA|µA|uA)", "Stop2 mode current"),
            (r"Standby[^\n]*?([\d\.]+)\s*(mA|µA|uA)", "Standby current"),
            (r"VBAT[^\n]*?([\d\.]+)\s*(mA|µA|uA)", "VBAT mode current"),
        ]

        if not results:
            for pattern, name in current_patterns:
                for m in re.finditer(pattern, text, re.IGNORECASE):
                    results.append({
                        "section": "current_consumption",
                        "parameter": name,
                        "min_value": "-",
                        "typ_value": m.group(1),
                        "max_value": "-",
                        "unit": m.group(2),
                        "conditions": "",
                        "source_page": page_num,
                        "raw_text": m.group(0).strip(),
                        "confidence": 0.7,
                    })

        return results

    # ──────────────────────────────────────────────────────────────────────────
    # Thermal characteristics
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_thermal(self, text: str, page_num: int) -> List[Dict[str, Any]]:
        results = []

        m_ja = THETA_JA_PATTERN.search(text)
        if m_ja:
            results.append({
                "section": "thermal",
                "parameter": "θJA — Junction-to-Ambient Thermal Resistance",
                "min_value": "-",
                "typ_value": m_ja.group(1),
                "max_value": "-",
                "unit": m_ja.group(2),
                "conditions": "Still air",
                "source_page": page_num,
                "raw_text": m_ja.group(0).strip(),
                "confidence": 0.95,
            })

        m_jc = THETA_JC_PATTERN.search(text)
        if m_jc:
            results.append({
                "section": "thermal",
                "parameter": "θJC — Junction-to-Case Thermal Resistance",
                "min_value": "-",
                "typ_value": m_jc.group(1),
                "max_value": "-",
                "unit": m_jc.group(2),
                "conditions": "",
                "source_page": page_num,
                "raw_text": m_jc.group(0).strip(),
                "confidence": 0.95,
            })

        # Temp range
        m_temp = re.search(r"(-?\d+)\s*°?C?\s*to\s*(-?\d+)\s*°?C?\s*(operating|junction)", text, re.IGNORECASE)
        if m_temp:
            results.append({
                "section": "thermal",
                "parameter": "Junction / Operating Temperature Range",
                "min_value": m_temp.group(1),
                "typ_value": "-",
                "max_value": m_temp.group(2),
                "unit": "°C",
                "conditions": "Operating",
                "source_page": page_num,
                "raw_text": m_temp.group(0).strip(),
                "confidence": 0.9,
            })

        return results

    # ──────────────────────────────────────────────────────────────────────────
    # Features surface (cover page bullets)
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_features(self, text: str, page_num: int) -> List[Dict[str, Any]]:
        results = []
        # Only if this looks like a features page
        if "features" not in text.lower() and "product" not in text.lower():
            return results

        for m in FEATURE_BULLET_PATTERN.finditer(text):
            feature_text = m.group(1).strip()
            if len(feature_text) < 5:
                continue
            results.append({
                "section": "features",
                "parameter": feature_text[:120],
                "min_value": "-",
                "typ_value": "-",
                "max_value": "-",
                "unit": "",
                "conditions": "",
                "source_page": page_num,
                "raw_text": feature_text,
                "confidence": 0.75,
            })

        return results


if __name__ == "__main__":
    import sys
    import json

    pdf = sys.argv[1] if len(sys.argv) > 1 else "data/stm32_datasheets/STM32H743_datasheet.pdf"
    mpn = sys.argv[2] if len(sys.argv) > 2 else "STM32H743"

    extractor = DeepDatasheetExtractor(pdf, mpn)
    params = extractor.extract_all()
    print(f"Extracted {len(params)} parameters from {pdf}")

    # Group by section
    sections: Dict[str, int] = {}
    for p in params:
        sections[p["section"]] = sections.get(p["section"], 0) + 1
    for sec, count in sorted(sections.items()):
        print(f"  {sec}: {count} params")

    if "--json" in sys.argv:
        print(json.dumps(params[:20], indent=2))
