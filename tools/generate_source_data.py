"""Write the SAP, FPIMS and PVSS source files to a local folder.

The generator lives in src/notebooks/source_systems.py, the notebook that 02_source_data runs in Databricks.
Run: python tools/generate_source_data.py <output_dir>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "notebooks"))

from source_systems import *  # noqa: E402,F401,F403
from source_systems import generate_all  # noqa: E402

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "source_data"
    result = generate_all(target)
    for name, n in result.items():
        print(f"{n:>7,}  {name}")
    print(f"{sum(result.values()):>7,}  total")
