"""Include the packaged manifest helper's regression cases in repository CI."""

import importlib.util
from pathlib import Path
import unittest


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str) -> unittest.TestSuite:
    path = Path(__file__).resolve().parents[1] / "plugins" / "skill-sync" / "evals" / "test_skill_manifest.py"
    spec = importlib.util.spec_from_file_location("skill_sync_manifest_tests", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return loader.loadTestsFromModule(module)
