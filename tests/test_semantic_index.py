import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

import numpy as np
from tools.semantic_index import SemanticSearch, build_index, index_paths


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "samples", "tiny_export")


class FakeModel:
    def __init__(self, _name):
        pass

    def encode(self, values, **_kwargs):
        return np.asarray([[1.0, 0.0] if "login" in value.lower() else [0.0, 1.0] for value in values], dtype=np.float32)


class SemanticIndexTests(unittest.TestCase):
    def test_index_paths_are_export_local(self):
        directory, metadata, vectors = index_paths("example")
        self.assertIn(os.path.join("derived", "semantic"), directory)
        self.assertTrue(metadata.endswith("metadata.json"))
        self.assertTrue(vectors.endswith("vectors.npz"))

    def test_build_and_query_portable_index_without_chroma(self):
        fake_module = types.SimpleNamespace(SentenceTransformer=FakeModel)
        with tempfile.TemporaryDirectory() as temporary:
            export = os.path.join(temporary, "export")
            shutil.copytree(SAMPLE, export)
            with mock.patch.dict(sys.modules, {"sentence_transformers": fake_module}):
                result = build_index(export, "fixture-model", batch_size=2)
                self.assertEqual(2, result["function_count"])
                hits = SemanticSearch(export).search("login", 1)
            self.assertEqual("00401000", hits[0]["function"]["address"])
