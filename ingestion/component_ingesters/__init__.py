"""
Component Ingesters Package

Contains specialized ingesters for different component categories:
- PMICs (Power Management ICs)
- DC-DC Converters
- LDOs (Low Dropout Regulators)
- CAN Transceivers
- Sensors
- Memory
"""

from pathlib import Path

__version__ = "1.0.0"
__all__ = ["pmic_ingester", "dcdc_ingester", "ldo_ingester"]
