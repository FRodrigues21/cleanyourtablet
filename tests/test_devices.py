"""Checks every list in devices/, the protected lists, and the tables that index them.

Run from the repository root: python3 -m unittest discover -s tests -v
"""
import re
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import pad  # noqa: E402

DEVICES = ROOT / "devices"
FOLDER = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)+$")


def folders():
    return sorted(p for p in DEVICES.iterdir() if p.is_dir())


def table_rows(path, header_prefix):
    lines = path.read_text(encoding="utf-8").split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith(header_prefix))
    rows = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        rows.append(line)
    return rows


class DeviceListsTest(unittest.TestCase):
    def test_folder_names(self):
        for f in folders():
            with self.subTest(folder=f.name):
                self.assertRegex(f.name, FOLDER, "use lowercase <brand>-<model>, e.g. xiaomi-redmi-pad-2-pro")
                self.assertTrue((f / "debloat.txt").is_file(), "no debloat.txt")

    def test_list_format(self):
        for f in folders():
            path = f / "debloat.txt"
            with self.subTest(folder=f.name):
                lines = path.read_text(encoding="utf-8").split("\n")
                self.assertTrue(lines[0].startswith("# "), "first line names the tablet (tools/pad.py probe)")
                self.assertRegex(lines[0], r"Android \d+", "header needs the Android version")
                packages = []
                for n, line in enumerate(lines, 1):
                    body = line.split("#", 1)[0].strip()
                    if body:
                        self.assertRegex(body, pad.PACKAGE_RE, f"line {n}: not a package name: {line!r}")
                        packages.append(body)
                self.assertTrue(packages, "no packages")
                dupes = sorted({p for p in packages if packages.count(p) > 1})
                self.assertFalse(dupes, f"listed twice: {dupes}")

    def test_nothing_protected_is_listed(self):
        rules = pad.protected_rules()
        for f in folders():
            with self.subTest(folder=f.name):
                hit = [p for p in pad.read_list(f / "debloat.txt") if pad.is_protected(p, rules)]
                self.assertFalse(hit, f"in protected/: {hit}")

    def test_protected_lists_are_package_names(self):
        for f in sorted((ROOT / "protected").glob("*.txt")):
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                body = line.split("#", 1)[0].strip()
                if body:
                    with self.subTest(file=f.name, line=n):
                        name = body[:-2] if body.endswith(".*") else body
                        self.assertTrue(name == "android" or pad.PACKAGE_RE.match(name), body)

    def test_devices_table_matches_folders(self):
        rows = table_rows(DEVICES / "README.md", "| Folder |")
        listed = [re.match(r"\|\s*`([^`/]+)/`\s*\|", r).group(1) for r in rows]
        self.assertEqual(sorted(listed), [f.name for f in folders()],
                         "devices/README.md rows and devices/ folders differ")

    def test_readme_table_has_one_row_per_device(self):
        readme = table_rows(ROOT / "README.md", "| Tablet | OS |")
        devices = table_rows(DEVICES / "README.md", "| Folder |")
        self.assertEqual(sorted(r.split("|")[1].strip() for r in readme),
                         sorted(r.split("|")[2].strip() for r in devices),
                         "the Tablet column differs between README.md and devices/README.md")


if __name__ == "__main__":
    unittest.main()
