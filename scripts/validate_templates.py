import sys
from pathlib import Path
import yaml
from core.ontology import DeviceType

def validate_templates():
    template_dir = Path("templates")
    print(f"Scanning {template_dir}...")
    
    for yaml_file in template_dir.rglob("*.yaml"):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            device_type = data.get('device_type')
            print(f"[{yaml_file.name}] device_type: '{device_type}' (type: {type(device_type).__name__})")
            
            # Check against enum
            try:
                if isinstance(device_type, str):
                    DeviceType(device_type.lower())
                else:
                    print(f"  FAILED: device_type is not a string!")
            except ValueError:
                 print(f"  FAILED: '{device_type}' is not a valid DeviceType!")

        except Exception as e:
            print(f"Error reading {yaml_file}: {e}")

if __name__ == "__main__":
    validate_templates()
