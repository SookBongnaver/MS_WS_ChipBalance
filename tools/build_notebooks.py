"""Build participant .ipynb notebooks from src/notebooks/*.py (Databricks source format)."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "notebooks"
OUTPUT = ROOT / "notebooks"


def cells_from_source(path):
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if not lines or lines[0].strip() != "# Databricks notebook source":
        raise ValueError(f"{path.name}: missing '# Databricks notebook source' header")
    sections = [[]]
    for line in lines[1:]:
        if line.strip() == "# COMMAND ----------":
            sections.append([])
        else:
            sections[-1].append(line)
    cells = []
    for number, body in enumerate(sections, 1):
        while body and not body[0].strip():
            body.pop(0)
        while body and not body[-1].strip():
            body.pop()
        if not body:
            raise ValueError(f"{path.name}: empty cell {number}")
        if body[0].startswith("# MAGIC"):
            if not all(line.startswith("# MAGIC") for line in body):
                raise ValueError(f"{path.name}: cell {number} mixes MAGIC and Python")
            text = [line[len("# MAGIC "):] if line.startswith("# MAGIC ") else line[len("# MAGIC"):] for line in body]
            first = text[0].strip()
            if first == "%md":
                kind, text = "markdown", text[1:]
            elif first.startswith("%run "):
                kind = "code"
            else:
                raise ValueError(f"{path.name}: cell {number} has unsupported magic {first!r}")
        else:
            kind, text = "code", body
            compile("".join(text), f"{path.name} cell {number}", "exec")
        text[-1] = text[-1].rstrip("\n")
        digest = hashlib.sha256((kind + "".join(text)).encode("utf-8")).hexdigest()[:12]
        cell = {"cell_type": kind, "id": f"c{number:02d}-{digest}", "metadata": {}, "source": text}
        if kind == "code":
            cell.update(outputs=[], execution_count=None)
        cells.append(cell)
    return cells


def build():
    OUTPUT.mkdir(exist_ok=True)
    built = []
    for path in sorted(SOURCE.glob("*.py")):
        notebook = {
            "nbformat": 4, "nbformat_minor": 5,
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                         "language_info": {"name": "python"}},
            "cells": cells_from_source(path),
        }
        target = OUTPUT / f"{path.stem}.ipynb"
        target.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        built.append(target)
    return built


if __name__ == "__main__":
    for target in build():
        print("built", target.relative_to(ROOT))
