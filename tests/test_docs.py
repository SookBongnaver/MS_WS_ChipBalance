"""Checks for the workshop documents and participant notebooks (stdlib only)."""
import importlib.util
import json
import re
import types
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SOURCES = ROOT / "src" / "notebooks"
NOTEBOOKS = ROOT / "notebooks"

CHAPTERS = [
    "00-scenario.rst",
    "01-connect.rst",
    "02-source-data.rst",
    "03-bronze.rst",
    "04-silver.rst",
    "05-gold-onelake.rst",
    "06-emergency-order.rst",
    "07-genie.rst",
    "08-ontology.rst",
    "09-ontology-agent.rst",
    "10-power-bi.rst",
    "11-operations-agent.rst",
    "12-foundry-agent.rst",
    "13-finish.rst",
]
# Chapters that are still being written. While such a file is missing, the existence check and
# links pointing to it are reported as skipped. Empty this set once all chapters are written.
PENDING_CHAPTERS = set()

FORBIDDEN_WORDS = ["강사 승인", "승인 후", "approved_", "기본 실습", "확장 실습", "리허설", "워크숍"]
# The material describes only what to do now, never how it used to be.
HISTORY_PHRASES = ["기존 교재", "이전 교재", "이전 버전", "기존 방식", "이전 방식", "예전", "더 이상", "업로드하지",
                   "올리지 않", "업로드 대신", "올리는 대신", "바뀌었", "바꿨", "변경되었", "변경됐", "달라졌",
                   "재설계", "새로 바뀐", "새 방식"]

LINK = re.compile(r"(?<!`)`[^`<>]*<([^<>`]+)>`__?")
IMAGE = re.compile(r"^[ \t]*\.\.[ \t]+(?:image|figure)[ \t]?::[ \t]*(\S+)", re.MULTILINE)
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
# ".." that starts a comment: not a directive (name::), target (_), footnote ([) or substitution (|).
COMMENT_START = re.compile(r"^(\s*)\.\.(?:[ \t]+(?![ \t_\[|])(?![\w.+:-]+ ?::).*)?$")


def rel(path):
    return path.relative_to(ROOT).as_posix()


def strip_comments(text):
    """Remove RST comment blocks so commented-out links and images are not checked."""
    kept, comment_indent = [], None
    for line in text.splitlines():
        if comment_indent is not None:
            if not line.strip() or len(line) - len(line.lstrip()) > comment_indent:
                continue
            comment_indent = None
        match = COMMENT_START.match(line)
        if match:
            comment_indent = len(match.group(1))
            continue
        kept.append(line)
    return "\n".join(kept)


def rst_files():
    files = [ROOT / "README.rst", ROOT / "admin" / "README.rst", *sorted(DOCS.glob("*.rst"))]
    return [path for path in files if path.is_file()]


def is_pending(path):
    return path.parent == DOCS and path.name in PENDING_CHAPTERS and not path.exists()


class DocumentTests(unittest.TestCase):
    def test_required_documents_exist(self):
        for path in (ROOT / "README.rst", ROOT / "admin" / "README.rst"):
            with self.subTest(document=rel(path)):
                self.assertTrue(path.is_file(), f"{rel(path)} is missing")
        for name in CHAPTERS:
            path = DOCS / name
            with self.subTest(document=rel(path)):
                if is_pending(path):
                    self.skipTest(f"{rel(path)} is not written yet")
                self.assertTrue(path.is_file(), f"{rel(path)} is missing")

    def test_relative_links_resolve(self):
        for path in rst_files():
            for target in LINK.findall(strip_comments(path.read_text(encoding="utf-8"))):
                target = "".join(target.split())
                if SCHEME.match(target) or target.startswith("#") or target.endswith("_"):
                    continue
                resolved = (path.parent / target.split("#", 1)[0]).resolve()
                with self.subTest(document=rel(path), link=target):
                    if is_pending(resolved):
                        self.skipTest(f"{resolved.name} is not written yet")
                    self.assertTrue(resolved.exists(), f"{rel(path)}: broken link {target}")

    def test_images_exist(self):
        for path in rst_files():
            for target in IMAGE.findall(strip_comments(path.read_text(encoding="utf-8"))):
                if SCHEME.match(target):
                    continue
                with self.subTest(document=rel(path), image=target):
                    self.assertTrue((path.parent / target).is_file(), f"{rel(path)}: missing image {target}")

    def test_forbidden_words(self):
        for path in [ROOT / "README.rst", *sorted(DOCS.glob("*.rst"))]:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for word in FORBIDDEN_WORDS:
                with self.subTest(document=rel(path), word=word):
                    self.assertNotIn(word, text)

    def test_no_history_phrases(self):
        texts = {rel(path): path.read_text(encoding="utf-8")
                 for path in [*rst_files(), *sorted((ROOT / "admin").glob("*.rst")), ROOT / "assets" / "architecture.svg"]
                 if path.is_file()}
        for source in sorted(SOURCES.glob("*.py")):
            texts[rel(source)] = "\n".join(line for line in source.read_text(encoding="utf-8").splitlines()
                                           if line.startswith("# MAGIC"))
        for name, text in texts.items():
            for phrase in HISTORY_PHRASES:
                with self.subTest(document=name, phrase=phrase):
                    self.assertNotIn(phrase, text)


class NotebookTests(unittest.TestCase):
    def sources(self):
        sources = sorted(SOURCES.glob("*.py"))
        self.assertTrue(sources, "src/notebooks has no .py files")
        return sources

    def test_notebooks_are_clean_ipynb(self):
        for source in self.sources():
            target = NOTEBOOKS / f"{source.stem}.ipynb"
            with self.subTest(notebook=rel(target)):
                self.assertTrue(target.is_file(), f"{rel(target)} is missing; run python tools/build_notebooks.py")
                notebook = json.loads(target.read_text(encoding="utf-8"))
                self.assertEqual(notebook.get("nbformat"), 4)
                self.assertTrue(notebook.get("cells"))
                for cell in notebook["cells"]:
                    self.assertFalse(cell.get("outputs"), f"{rel(target)} has saved outputs")
                    if cell.get("cell_type") == "code":
                        self.assertIsNone(cell.get("execution_count"))

    def test_notebooks_match_sources(self):
        spec = importlib.util.spec_from_file_location("build_notebooks", ROOT / "tools" / "build_notebooks.py")
        build_notebooks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build_notebooks)
        for source in self.sources():
            target = NOTEBOOKS / f"{source.stem}.ipynb"
            if not target.is_file():
                continue
            with self.subTest(notebook=rel(target)):
                cells = json.loads(target.read_text(encoding="utf-8"))["cells"]
                self.assertEqual(cells, build_notebooks.cells_from_source(source),
                                 f"{rel(target)} differs from {rel(source)}; run python tools/build_notebooks.py")

    def test_import_archive_matches_notebooks(self):
        archive = NOTEBOOKS / "ChipBalance.zip"
        self.assertTrue(archive.is_file(), "notebooks/ChipBalance.zip is missing; run python tools/build_notebooks.py")
        with zipfile.ZipFile(archive) as bundle:
            names = sorted(bundle.namelist())
            expected = sorted(f"ChipBalance/{p.name}" for p in NOTEBOOKS.glob("*.ipynb"))
            self.assertEqual(names, expected)
            for name in names:
                with self.subTest(entry=name):
                    self.assertEqual(bundle.read(name), (NOTEBOOKS / name.split("/", 1)[1]).read_bytes(),
                                     f"{name} is stale; run python tools/build_notebooks.py")

    def setup_unity_catalog_cell(self):
        source = SOURCES / "01_setup.py"
        spec = importlib.util.spec_from_file_location("build_notebooks", ROOT / "tools" / "build_notebooks.py")
        build_notebooks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build_notebooks)
        return next("".join(cell["source"]) for cell in build_notebooks.cells_from_source(source)
                    if cell["cell_type"] == "code" and "CREATE CATALOG IF NOT EXISTS" in "".join(cell["source"]))

    def test_setup_prepares_and_checks_unity_catalog(self):
        setup_cell = self.setup_unity_catalog_cell()
        self.assertNotIn("import re", setup_cell)
        for name in ("participant", "catalog", "schema", "raw_volume", "fabric_workspace",
                     "fabric_lakehouse", "service_credential"):
            self.assertNotRegex(setup_cell, rf"(?m)^{name}\s*=")

        for participant in ("p001", "p002", "p037", "p999"):
            with self.subTest(participant=participant):
                statements = []

                class Spark:
                    conf = types.SimpleNamespace(set=lambda *args: None)

                    @staticmethod
                    def sql(statement):
                        statements.append(statement)

                schema = f"chipbalance_{participant}"
                catalog = f"lab_factory_{participant}"
                raw_volume = f"/Volumes/{catalog}/{schema}/raw"
                listed = []
                namespace = {
                    "re": re,
                    "participant": participant,
                    "catalog": catalog,
                    "schema": schema,
                    "raw_volume": raw_volume,
                    "spark": Spark(),
                    "dbutils": types.SimpleNamespace(
                        fs=types.SimpleNamespace(ls=lambda path: listed.append(path))
                    ),
                    "print": lambda *args: None,
                }
                exec(setup_cell, namespace)

                self.assertEqual(statements, [
                    f"CREATE CATALOG IF NOT EXISTS `{catalog}`",
                    f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`",
                    f"CREATE VOLUME IF NOT EXISTS `{catalog}`.`{schema}`.`raw`",
                    f"USE CATALOG `{catalog}`",
                    f"USE SCHEMA `{schema}`",
                ])
                self.assertEqual(listed, [raw_volume])

    def test_setup_rejects_invalid_participant(self):
        setup_cell = self.setup_unity_catalog_cell()
        for participant in ("p01", "p1000", "P001", "participant"):
            with self.subTest(participant=participant):
                schema = f"chipbalance_{participant}"
                namespace = {
                    "re": re,
                    "participant": participant,
                    "catalog": f"lab_factory_{participant}",
                    "schema": schema,
                    "raw_volume": f"/Volumes/lab_factory_{participant}/{schema}/raw",
                }
                with self.assertRaisesRegex(ValueError, "participant는 p001처럼"):
                    exec(setup_cell, namespace)


if __name__ == "__main__":
    unittest.main()
