
import subprocess
import sys

with open("debug_output.txt", "w") as f:
    # Use explicit python executable
    cmd = [sys.executable, "ingestion/stm32_datasheet_extractor.py", "datasheets/mock_stm32.pdf"]
    print(f"Running: {cmd}")
    subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    print("Done.")
