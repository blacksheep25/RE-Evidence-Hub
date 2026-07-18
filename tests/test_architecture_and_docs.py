import ast
import os
import re
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST_ONLY = {"flask", "requests", "chromadb", "sentence_transformers", "numpy"}


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_ghidra_runtime_does_not_import_host_only_dependencies(self):
        roots = [os.path.join(ROOT, "exporters"), os.path.join(ROOT, "util")]
        offenders = []
        for base in roots:
            for directory, _subdirs, files in os.walk(base):
                for name in files:
                    if not name.endswith(".py"):
                        continue
                    path = os.path.join(directory, name)
                    with open(path, encoding="utf-8", errors="replace") as handle:
                        tree = ast.parse(handle.read(), filename=path)
                    for node in ast.walk(tree):
                        names = []
                        if isinstance(node, ast.Import):
                            names = [alias.name.split(".")[0] for alias in node.names]
                        elif isinstance(node, ast.ImportFrom) and node.module:
                            names = [node.module.split(".")[0]]
                        for imported in names:
                            if imported in HOST_ONLY:
                                offenders.append("{} imports {}".format(os.path.relpath(path, ROOT), imported))
        self.assertEqual([], offenders)


class DocumentationLinkTests(unittest.TestCase):
    def test_relative_markdown_links_resolve(self):
        files = [os.path.join(ROOT, "README.md")]
        files += [os.path.join(ROOT, "docs", name) for name in os.listdir(os.path.join(ROOT, "docs")) if name.endswith(".md")]
        missing = []
        pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        for path in files:
            with open(path, encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            for target in pattern.findall(content):
                clean = target.split("#", 1)[0]
                if not clean or "://" in clean or clean.startswith("#"):
                    continue
                resolved = os.path.normpath(os.path.join(os.path.dirname(path), clean))
                if not os.path.exists(resolved):
                    missing.append("{} -> {}".format(os.path.relpath(path, ROOT), target))
        self.assertEqual([], missing)
