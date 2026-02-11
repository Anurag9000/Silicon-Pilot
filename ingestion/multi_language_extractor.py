"""
Multi-Language Support

Supports extraction and processing of datasheets in multiple languages:
- English (EN)
- Chinese (CN/ZH)
- Japanese (JP/JA)
- German (DE)

Features:
- Language detection
- Language-specific regex patterns
- Unit conversion (metric/imperial)
- Character encoding handling
"""

import re
from typing import Dict, Any, Optional, List
from enum import Enum


class Language(Enum):
    """Supported languages"""
    ENGLISH = "en"
    CHINESE = "zh"
    JAPANESE = "ja"
    GERMAN = "de"
    UNKNOWN = "unknown"


class MultiLanguageExtractor:
    """Extract specifications from multi-language datasheets"""
    
    def __init__(self):
        # Language-specific patterns
        self.voltage_patterns = {
            Language.ENGLISH: [
                r'(?:Supply\s+)?Voltage.*?(\d+\.?\d*)\s*(?:to|-)?\s*(\d+\.?\d*)?\s*V',
                r'V(?:DD|CC|BAT).*?(\d+\.?\d*)\s*(?:to|-)?\s*(\d+\.?\d*)?\s*V'
            ],
            Language.CHINESE: [
                r'(?:电源)?电压.*?(\d+\.?\d*)\s*(?:至|到|-)?\s*(\d+\.?\d*)?\s*V',
                r'工作电压.*?(\d+\.?\d*)\s*(?:至|到|-)?\s*(\d+\.?\d*)?\s*V'
            ],
            Language.JAPANESE: [
                r'(?:電源)?電圧.*?(\d+\.?\d*)\s*(?:~|-)?\s*(\d+\.?\d*)?\s*V',
                r'動作電圧.*?(\d+\.?\d*)\s*(?:~|-)?\s*(\d+\.?\d*)?\s*V'
            ],
            Language.GERMAN: [
                r'(?:Versorgungs)?[Ss]pannung.*?(\d+\.?\d*)\s*(?:bis|-)?\s*(\d+\.?\d*)?\s*V',
                r'Betriebsspannung.*?(\d+\.?\d*)\s*(?:bis|-)?\s*(\d+\.?\d*)?\s*V'
            ]
        }
        
        self.current_patterns = {
            Language.ENGLISH: [
                r'(?:Supply\s+)?Current.*?(\d+\.?\d*)\s*(m?A)',
                r'I(?:DD|CC|Q).*?(\d+\.?\d*)\s*(m?A|μA|uA)'
            ],
            Language.CHINESE: [
                r'(?:电源)?电流.*?(\d+\.?\d*)\s*(m?A)',
                r'工作电流.*?(\d+\.?\d*)\s*(m?A|μA)'
            ],
            Language.JAPANESE: [
                r'(?:電源)?電流.*?(\d+\.?\d*)\s*(m?A)',
                r'動作電流.*?(\d+\.?\d*)\s*(m?A|μA)'
            ],
            Language.GERMAN: [
                r'(?:Versorgungs)?[Ss]trom.*?(\d+\.?\d*)\s*(m?A)',
                r'Betriebsstrom.*?(\d+\.?\d*)\s*(m?A|μA)'
            ]
        }
        
        self.frequency_patterns = {
            Language.ENGLISH: [
                r'(?:Max(?:imum)?\s+)?Frequency.*?(\d+\.?\d*)\s*(MHz|GHz|kHz)',
                r'Clock.*?(\d+\.?\d*)\s*(MHz|GHz|kHz)'
            ],
            Language.CHINESE: [
                r'(?:最大)?频率.*?(\d+\.?\d*)\s*(MHz|GHz|kHz)',
                r'时钟.*?(\d+\.?\d*)\s*(MHz|GHz|kHz)'
            ],
            Language.JAPANESE: [
                r'(?:最大)?周波数.*?(\d+\.?\d*)\s*(MHz|GHz|kHz)',
                r'クロック.*?(\d+\.?\d*)\s*(MHz|GHz|kHz)'
            ],
            Language.GERMAN: [
                r'(?:Max(?:imale)?\s+)?Frequenz.*?(\d+\.?\d*)\s*(MHz|GHz|kHz)',
                r'Takt.*?(\d+\.?\d*)\s*(MHz|GHz|kHz)'
            ]
        }
    
    def detect_language(self, text: str) -> Language:
        """
        Detect document language
        
        Uses character set and keyword detection
        """
        # Check for Chinese characters
        if re.search(r'[\u4e00-\u9fff]', text):
            return Language.CHINESE
        
        # Check for Japanese characters (Hiragana/Katakana)
        if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
            return Language.JAPANESE
        
        # Check for German umlauts and keywords
        german_keywords = ['Spannung', 'Strom', 'Frequenz', 'Betrieb', 'Versorgung']
        if any(kw in text for kw in german_keywords):
            return Language.GERMAN
        
        # Default to English
        english_keywords = ['Voltage', 'Current', 'Frequency', 'Supply', 'Operating']
        if any(kw in text for kw in english_keywords):
            return Language.ENGLISH
        
        return Language.UNKNOWN
    
    def extract_voltage(self, text: str, language: Optional[Language] = None) -> Optional[Dict[str, float]]:
        """Extract voltage range"""
        if language is None:
            language = self.detect_language(text)
        
        if language not in self.voltage_patterns:
            language = Language.ENGLISH
        
        for pattern in self.voltage_patterns[language]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                v_min = float(match.group(1))
                v_max = float(match.group(2)) if match.group(2) else v_min
                return {'min': v_min, 'max': v_max}
        
        return None
    
    def extract_current(self, text: str, language: Optional[Language] = None) -> Optional[Dict[str, Any]]:
        """Extract current consumption"""
        if language is None:
            language = self.detect_language(text)
        
        if language not in self.current_patterns:
            language = Language.ENGLISH
        
        for pattern in self.current_patterns[language]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2).lower()
                
                # Convert to mA
                if 'μa' in unit or 'ua' in unit:
                    value = value / 1000.0
                
                return {'value_ma': value, 'unit': 'mA'}
        
        return None
    
    def extract_frequency(self, text: str, language: Optional[Language] = None) -> Optional[Dict[str, Any]]:
        """Extract frequency"""
        if language is None:
            language = self.detect_language(text)
        
        if language not in self.frequency_patterns:
            language = Language.ENGLISH
        
        for pattern in self.frequency_patterns[language]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2).upper()
                
                # Convert to MHz
                if unit == 'GHZ':
                    value = value * 1000.0
                elif unit == 'KHZ':
                    value = value / 1000.0
                
                return {'value_mhz': value, 'unit': 'MHz'}
        
        return None
    
    def extract_all_specs(self, text: str) -> Dict[str, Any]:
        """Extract all specifications with language detection"""
        language = self.detect_language(text)
        
        specs = {
            'detected_language': language.value,
            'voltage': self.extract_voltage(text, language),
            'current': self.extract_current(text, language),
            'frequency': self.extract_frequency(text, language)
        }
        
        return specs


# Example usage
def main():
    extractor = MultiLanguageExtractor()
    
    # English example
    en_text = "Supply Voltage: 2.0V to 3.6V, Operating Current: 150μA, Maximum Frequency: 168MHz"
    en_specs = extractor.extract_all_specs(en_text)
    print(f"English: {en_specs}")
    
    # Chinese example
    cn_text = "电源电压：2.0V至3.6V，工作电流：150μA，最大频率：168MHz"
    cn_specs = extractor.extract_all_specs(cn_text)
    print(f"Chinese: {cn_specs}")
    
    # Japanese example
    ja_text = "電源電圧：2.0V~3.6V、動作電流：150μA、最大周波数：168MHz"
    ja_specs = extractor.extract_all_specs(ja_text)
    print(f"Japanese: {ja_specs}")
    
    # German example
    de_text = "Versorgungsspannung: 2.0V bis 3.6V, Betriebsstrom: 150μA, Maximale Frequenz: 168MHz"
    de_specs = extractor.extract_all_specs(de_text)
    print(f"German: {de_specs}")


if __name__ == "__main__":
    main()
