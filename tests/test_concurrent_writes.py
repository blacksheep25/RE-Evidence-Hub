import json
import multiprocessing
import os
import unittest

from tests.test_agent_mcp import make_export


def _annotate_worker(export_path, address, name):
    from tools.function_annotations import annotate
    annotate(export_path, address, name, "medium", evidence=["concurrency fixture"], rationale="Concurrent writer regression fixture.")


class ConcurrentWriteTests(unittest.TestCase):
    def test_two_annotation_processes_preserve_both_updates(self):
        temporary = make_export()
        self.addCleanup(temporary.cleanup)
        processes = [
            multiprocessing.Process(target=_annotate_worker, args=(temporary.name, "00401000", "Fixture_First")),
            multiprocessing.Process(target=_annotate_worker, args=(temporary.name, "00402000", "Fixture_Second")),
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(15)
            self.assertEqual(0, process.exitcode)
        path = os.path.join(temporary.name, "annotations", "function_names.json")
        with open(path, encoding="utf-8") as handle:
            overlay = json.load(handle)
        self.assertEqual({"00401000", "00402000"}, set(overlay["entries"]))
        self.assertEqual(2, overlay["revision"])
