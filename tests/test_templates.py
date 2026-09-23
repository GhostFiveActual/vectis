# GHOST FIVE // VECTIS
# Regression coverage for deterministic built-in project templates.
from __future__ import annotations

from pathlib import Path, PurePosixPath
import tempfile
import unittest

from vectis.product import test_project
from vectis.templates import (
    TEMPLATE_SCHEMA,
    template_catalog,
    template_preview,
    write_project_template,
)


class ProjectTemplateTests(unittest.TestCase):
    def test_catalog_is_stable_and_sorted(self) -> None:
        first = template_catalog()
        second = template_catalog()

        self.assertEqual(first, second)
        self.assertEqual(
            first["schema"],
            TEMPLATE_SCHEMA,
        )
        ids = [
            item["id"]
            for item in first["templates"]
        ]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(
            ids,
            [
                "filesystem-action",
                "release-gate",
                "starter",
            ],
        )

    def test_preview_is_deterministic_and_hashes_content(self) -> None:
        first = template_preview("release-gate")
        second = template_preview("release-gate")

        self.assertEqual(first, second)
        self.assertEqual(
            first["schema"],
            TEMPLATE_SCHEMA,
        )
        self.assertTrue(first["files"])
        for item in first["files"]:
            self.assertEqual(
                len(item["sha256"]),
                64,
            )
            path = PurePosixPath(item["path"])
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)

    def test_every_template_materializes_and_compiles(self) -> None:
        for item in template_catalog()["templates"]:
            with self.subTest(template=item["id"]):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory) / item["id"]
                    created = write_project_template(
                        item["id"],
                        root,
                    )
                    self.assertEqual(
                        len(created),
                        item["file_count"],
                    )
                    result = test_project(root)
                    self.assertGreaterEqual(
                        result["files"],
                        1,
                    )
                    self.assertEqual(
                        result["failed"],
                        0,
                    )

    def test_writer_fails_closed_on_collision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = write_project_template(
                "release-gate",
                root,
            )
            self.assertTrue(first)

            with self.assertRaises(
                FileExistsError
            ):
                write_project_template(
                    "release-gate",
                    root,
                )

            replaced = write_project_template(
                "release-gate",
                root,
                force=True,
            )
            self.assertEqual(
                len(replaced),
                len(first),
            )

        with self.assertRaisesRegex(
            ValueError,
            "unknown",
        ):
            template_preview(
                "missing-template"
            )


if __name__ == "__main__":
    unittest.main()
