"""Write the SAP, FPIMS and PVSS source files to a local folder.

The generator lives in notebooks/source_systems.ipynb, the notebook that 02_source_data runs in Databricks.
Run: python tools/generate_source_data.py <output_dir>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import notebook_source  # noqa: E402

exec(compile(notebook_source.code(notebook_source.NOTEBOOKS / "source_systems.ipynb"),
             "source_systems.ipynb", "exec"))

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "source_data"
    result = generate_all(target)  # noqa: F821
    for name, n in result.items():
        print(f"{n:>7,}  {name}")
    print(f"{sum(result.values()):>7,}  total")
