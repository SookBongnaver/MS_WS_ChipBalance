"""Read the .ipynb notebooks, which are the only source of the workshop notebooks and the admin notebook."""
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"
ADMIN = ROOT / "admin"
ARCHIVE = NOTEBOOKS / "ChipBalance.zip"
ARCHIVE_FOLDER = "ChipBalance"


def cells(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))["cells"]


def cell_text(cell):
    return "".join(cell["source"])


def code_cells(path):
    """Python code cells, without cells that start with a notebook magic such as %pip or %run."""
    return [cell_text(c) for c in cells(path)
            if c["cell_type"] == "code" and not cell_text(c).lstrip().startswith("%")]


def code(path):
    """All Python code cells joined, so the notebook can be parsed or executed as one module."""
    return "\n\n".join(code_cells(path))


def markdown(path):
    return "\n\n".join(cell_text(c) for c in cells(path) if c["cell_type"] == "markdown")


def build_archive():
    """One ZIP for Databricks Import: it creates the ChipBalance folder with every notebook."""
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(NOTEBOOKS.glob("*.ipynb")):
            info = zipfile.ZipInfo(f"{ARCHIVE_FOLDER}/{path.name}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return ARCHIVE


if __name__ == "__main__":
    print("built", build_archive().relative_to(ROOT))
