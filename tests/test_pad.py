"""Exercise tools/pad.py against a fake adb, without a tablet.

Run from the repository root: python3 -m unittest discover -s tests -v
"""
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import pad  # noqa: E402


class PadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        adb = bin_dir / "adb"
        adb.write_text(f'#!/bin/sh\nexec "{sys.executable}" -I "{ROOT / "tests" / "fake_adb.py"}" "$@"\n')
        adb.chmod(adb.stat().st_mode | stat.S_IEXEC)
        self.state = self.tmp / "state.json"
        self.env = mock.patch.dict(os.environ, {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "FAKE_ADB_STATE": str(self.state),
            "PAD_STATE_DIR": str(self.tmp / "records"),
        })
        self.env.start()
        os.environ.pop("PAD_SERIAL", None)
        self.write_state({"packages": {
            "com.miui.analytics": "enabled",
            "com.miui.msa.global": "enabled",
            "com.netflix.mediaclient": "disabled",   # the owner disabled it before
            "com.xiaomi.stubborn": "enabled",       # HyperOS refuses disable-user for this one
        }, "refuse_disable": ["com.xiaomi.stubborn"]})

    def tearDown(self):
        self.env.stop()

    def write_state(self, st):
        self.state.write_text(json.dumps(st))

    def read_state(self):
        return json.loads(self.state.read_text())

    def write_list(self, text, name="debloat.txt"):
        d = self.tmp / "devices" / "test-tablet"
        d.mkdir(parents=True, exist_ok=True)
        p = d / name
        p.write_bytes(text if isinstance(text, bytes) else text.encode())
        return str(p)

    def run_pad(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = pad.main(list(args))
        return code, out.getvalue(), err.getvalue()

    LIST = ("# Test tablet, Android 16\n"
            "com.miui.analytics\n"
            "com.miui.msa.global   # ads\n"
            "com.netflix.mediaclient\n"
            "com.xiaomi.stubborn\n"
            "com.not.installed\n")

    def test_disable_then_restore_round_trip(self):
        lst = self.write_list(self.LIST)
        code, out, _ = self.run_pad("disable", lst)
        self.assertEqual(code, 0, out)
        pk = self.read_state()["packages"]
        self.assertEqual(pk["com.miui.analytics"], "disabled")
        self.assertEqual(pk["com.xiaomi.stubborn"], "removed", "fallback to uninstall --user 0")
        self.assertIn("uninstall", out)

        code, out, _ = self.run_pad("restore", lst)
        self.assertEqual(code, 0, out)
        pk = self.read_state()["packages"]
        self.assertEqual(pk["com.miui.analytics"], "enabled")
        self.assertEqual(pk["com.miui.msa.global"], "enabled")
        self.assertEqual(pk["com.xiaomi.stubborn"], "enabled")
        self.assertEqual(pk["com.netflix.mediaclient"], "disabled", "was disabled before; stays disabled")
        log = self.read_state()["log"]
        self.assertIn("cmd package install-existing --user 0 com.xiaomi.stubborn", log)
        self.assertIn("pm enable --user 0 com.miui.analytics", log)

    def test_retry_keeps_the_first_record(self):
        lst = self.write_list(self.LIST)
        self.run_pad("disable", lst)
        self.run_pad("disable", lst)  # everything is disabled now; must not be recorded as "before"
        self.run_pad("restore", lst)
        self.assertEqual(self.read_state()["packages"]["com.miui.analytics"], "enabled")

    def test_restore_without_record_brings_everything_back(self):
        st = self.read_state()
        st["packages"]["com.miui.analytics"] = "removed"
        self.write_state(st)
        lst = self.write_list(self.LIST)
        code, _, err = self.run_pad("restore", lst)
        self.assertEqual(code, 0)
        self.assertIn("no record", err)
        pk = self.read_state()["packages"]
        self.assertEqual(pk["com.miui.analytics"], "enabled")
        self.assertEqual(pk["com.netflix.mediaclient"], "enabled")

    def test_injected_command_is_refused_before_connecting(self):
        lst = self.write_list("# t\ncom.miui.analytics; reboot\n")
        code, _, err = self.run_pad("disable", lst)
        self.assertEqual(code, 1)
        self.assertIn("not a package name", err)
        self.assertNotIn("log", self.read_state(), "nothing may reach the tablet")

    def test_protected_package_is_refused(self):
        lst = self.write_list("# t\ncom.miui.securitycenter\ncom.android.providers.settings\n")
        code, _, err = self.run_pad("disable", lst)
        self.assertEqual(code, 1)
        self.assertIn("com.miui.securitycenter", err)
        self.assertIn("com.android.providers.settings", err, "prefix rule")
        self.assertNotIn("log", self.read_state())

    def test_windows_bom_and_crlf(self):
        lst = self.write_list(b"\xef\xbb\xbf# t\r\ncom.miui.analytics\r\ncom.miui.msa.global # x\r\n")
        self.assertEqual(pad.read_list(lst), ["com.miui.analytics", "com.miui.msa.global"])

    def test_optional_lines_are_read_but_prose_is_not(self):
        lst = self.write_list("# t\n# com.miui.notes        # back up first\n#com.miui.player\n"
                              "# com.miui.daemon and com.miui.miservice are kept\ncom.miui.analytics\n")
        self.assertEqual(pad.read_optional(lst), ["com.miui.notes", "com.miui.player"])
        self.assertEqual(pad.read_list(lst), ["com.miui.analytics"])

    def test_limit_stops_and_a_rerun_continues(self):
        lst = self.write_list(self.LIST)
        self.run_pad("disable", "--limit", "1", lst)
        pk = self.read_state()["packages"]
        self.assertEqual([pk["com.miui.analytics"], pk["com.miui.msa.global"]], ["disabled", "enabled"])
        self.run_pad("disable", "--limit", "1", lst)
        self.assertEqual(self.read_state()["packages"]["com.miui.msa.global"], "disabled")
        self.run_pad("restore", lst)  # the second run must not have recorded analytics as "disabled before"
        self.assertEqual(self.read_state()["packages"]["com.miui.analytics"], "enabled")

    def test_dry_run_changes_nothing(self):
        lst = self.write_list(self.LIST)
        code, out, _ = self.run_pad("disable", "--dry-run", lst)
        self.assertEqual(code, 0)
        self.assertIn("would disable: com.miui.analytics", out)
        st = self.read_state()
        self.assertEqual(st["packages"]["com.miui.analytics"], "enabled")
        self.assertFalse(any(c.startswith("pm disable") for c in st["log"]))
        self.assertFalse((self.tmp / "records").exists() and any((self.tmp / "records").rglob("*.json")))

    def test_tweak_and_undo(self):
        st = self.read_state()
        st["settings"] = {"global/private_dns_mode": "opportunistic"}
        self.write_state(st)
        self.run_pad("tweak", "private-dns")
        self.run_pad("tweak", "private-dns")  # twice: undo must still go back to the original
        s = self.read_state()["settings"]
        self.assertEqual(s["global/private_dns_mode"], "hostname")
        self.assertEqual(s["global/private_dns_specifier"], "dns.adguard-dns.com")
        code, _, _ = self.run_pad("tweak", "private-dns", "--undo")
        self.assertEqual(code, 0)
        s = self.read_state()["settings"]
        self.assertEqual(s["global/private_dns_mode"], "opportunistic")
        self.assertNotIn("global/private_dns_specifier", s, "was unset before, so it is deleted")

    def test_several_devices_need_a_serial(self):
        st = self.read_state()
        st["devices"] = ["a", "b"]
        self.write_state(st)
        lst = self.write_list(self.LIST)
        code, _, err = self.run_pad("diff", lst)
        self.assertEqual(code, 1)
        self.assertIn("--serial", err)
        code, _, _ = self.run_pad("--serial", "a", "diff", lst)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
