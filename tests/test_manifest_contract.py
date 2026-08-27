from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import validate_repo


class ManifestContractTests(unittest.TestCase):
    def test_rejects_an_unknown_plugin_manifest_field(self) -> None:
        with self.assertRaises(validate_repo.ValidationError):
            validate_repo.reject_unknown_fields(
                {"name": "sample", "unsupported": True},
                validate_repo.ALLOWED_PLUGIN_FIELDS,
                "plugin manifest",
            )

    def test_rejects_an_unknown_plugin_interface_field(self) -> None:
        with self.assertRaises(validate_repo.ValidationError):
            validate_repo.reject_unknown_fields(
                {"displayName": "Sample", "unsupported": True},
                validate_repo.ALLOWED_PLUGIN_INTERFACE_FIELDS,
                "plugin interface",
            )

    def test_rejects_missing_or_escaping_plugin_assets(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            plugin_dir = Path(temporary_directory)
            with self.assertRaises(validate_repo.ValidationError):
                validate_repo.validate_plugin_asset(
                    plugin_dir,
                    "../outside.png",
                    "plugin icon",
                )
            with self.assertRaises(validate_repo.ValidationError):
                validate_repo.validate_plugin_asset(
                    plugin_dir,
                    "./assets/missing.png",
                    "plugin icon",
                )


if __name__ == "__main__":
    unittest.main()
