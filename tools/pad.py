#!/usr/bin/env python3
"""Debloat an Android tablet over ADB, reversibly. Standard library only; needs the `adb` binary.

    pad.py probe                          print the header line for a new debloat.txt
    pad.py backup [dir]                   save package lists, getprop and settings
    pad.py scaffold [--out FILE]          draft a debloat.txt for this tablet from every list in devices/
    pad.py diff <list>                    what in the list is enabled, disabled or missing here
    pad.py disable <list> [--batch N | --limit N] [--dry-run] [--force]
    pad.py restore <list> [--dry-run]     put back what disable changed, from its record
    pad.py tweak <private-dns|animations> [--undo]

The tablet is picked with --serial, else $PAD_SERIAL, else the only device `adb devices` shows.
Records of what was changed live in ~/.cleanyourtablet/ (or $PAD_STATE_DIR).
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
# Every name from a list or from the tablet ends up inside a command run by the tablet's shell, so
# nothing that could carry shell syntax is allowed through.
PACKAGE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$")
SETTING_RE = re.compile(r"^[\w.:-]*$")
VERSION = 1

TWEAKS = {
    # Ad-blocking DNS for every app. Does not block YouTube ads.
    "private-dns": [("global", "private_dns_mode", "hostname"),
                    ("global", "private_dns_specifier", "dns.adguard-dns.com")],
    # Half-length animations: the tablet feels faster, nothing is turned off.
    "animations": [("global", "window_animation_scale", "0.5"),
                   ("global", "transition_animation_scale", "0.5"),
                   ("global", "animator_duration_scale", "0.5")],
}


class PadError(Exception):
    pass


# ---------------------------------------------------------------- lists

def read_list(path):
    """Package names from a debloat list, in file order.

    A BOM and CRLF from a Windows editor are dropped, as is a trailing `# note`. Any line that is not
    a bare package name refuses the whole list, since a list may come from anyone.
    """
    text = Path(path).read_text(encoding="utf-8-sig")
    names, bad = [], []
    for n, line in enumerate(text.splitlines(), 1):
        body = line.split("#", 1)[0].strip()
        if not body:
            continue
        if PACKAGE_RE.match(body):
            if body not in names:
                names.append(body)
        else:
            bad.append(f"  line {n}: {line.strip()!r}")
    if bad:
        raise PadError(f"refusing {path}: not a package name:\n" + "\n".join(bad))
    return names


def protected_rules():
    """Names from protected/*.txt. A trailing `.*` protects every package under that prefix."""
    exact, prefixes = set(), []
    for f in sorted((ROOT / "protected").glob("*.txt")):
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            body = line.split("#", 1)[0].strip()
            if body.endswith(".*"):
                prefixes.append(body[:-1])
            elif body:
                exact.add(body)
    return exact, prefixes


def is_protected(pkg, rules=None):
    exact, prefixes = rules or protected_rules()
    return pkg in exact or any(pkg.startswith(p) for p in prefixes)


def device_lists():
    return sorted((ROOT / "devices").glob("*/debloat.txt"))


OPTIONAL_RE = re.compile(r"^#\s*([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+)\s*(#.*)?$")


def read_optional(path):
    """Commented-out `# package` lines: apps a list leaves for each owner to choose."""
    names = []
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        m = OPTIONAL_RE.match(line.strip())
        if m and m.group(1) not in names:
            names.append(m.group(1))
    return names


# ---------------------------------------------------------------- adb

class Tablet:
    def __init__(self, serial=None):
        self.adb = shutil.which("adb")
        if not self.adb:
            raise PadError("adb not found: install Android platform-tools and put adb on PATH")
        self.serial = serial or os.environ.get("PAD_SERIAL") or self._only_device()

    def _only_device(self):
        out = subprocess.run([self.adb, "devices"], capture_output=True, text=True).stdout
        ready = [l.split()[0] for l in out.splitlines()[1:] if l.strip().endswith("\tdevice")]
        if len(ready) == 1:
            return ready[0]
        if not ready:
            raise PadError("no tablet connected. Pair it first: adb pair <ip>:<pairing port>, then "
                           "adb connect <ip>:<port> (both shown under Developer options > Wireless debugging)")
        raise PadError("several devices connected, pick one with --serial or PAD_SERIAL:\n  "
                       + "\n  ".join(ready))

    def sh(self, command, check=True):
        """Run one shell command on the tablet and return its output (stdout and stderr together)."""
        p = subprocess.run([self.adb, "-s", self.serial, "shell", command],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                           encoding="utf-8", errors="replace")
        if check and p.returncode not in (0, 1) and not p.stdout:
            raise PadError(f"adb failed ({p.returncode}) running: {command}")
        return p.stdout.replace("\r\n", "\n")

    def prop(self, name):
        return self.sh(f"getprop {name}").strip()

    def packages(self, flag=""):
        out = self.sh(f"pm list packages {flag}".strip())
        return {l[len("package:"):].strip() for l in out.splitlines() if l.startswith("package:")}

    def states(self):
        """{package: 'enabled' | 'disabled' | 'removed'} for every package the system knows.

        'removed' means installed on the system but uninstalled for user 0 (pm uninstall -k --user 0).
        """
        everything = self.packages("-u")
        installed = self.packages()
        disabled = self.packages("-d")
        return {p: ("removed" if p not in installed else "disabled" if p in disabled else "enabled")
                for p in everything}

    def get_setting(self, ns, key):
        return self.sh(f"settings get {ns} {key}").strip()

    def put_setting(self, ns, key, value):
        if value in ("null", ""):
            self.sh(f"settings delete {ns} {key}")
        else:
            self.sh(f"settings put {ns} {key} {value}")


def safe_name(s):
    return re.sub(r"[^A-Za-z0-9._-]", "_", s)


# ---------------------------------------------------------------- records

def state_dir(serial):
    base = Path(os.environ.get("PAD_STATE_DIR") or Path.home() / ".cleanyourtablet")
    d = base / safe_name(serial)
    d.mkdir(parents=True, exist_ok=True)
    return d


def record_path(serial, list_path):
    p = Path(list_path).resolve()
    digest = hashlib.sha1(str(p).encode()).hexdigest()[:10]
    return state_dir(serial) / f"{safe_name(p.parent.name)}-{digest}.json"


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def save_json(path, data):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


# ---------------------------------------------------------------- commands

def cmd_probe(t, args):
    name = t.prop("ro.product.marketname") or t.prop("ro.product.model")
    maker = t.prop("ro.product.manufacturer")
    if maker and not name.lower().startswith(maker.lower()):
        name = f"{maker} {name}"
    os_name = t.prop("ro.mi.os.version.incremental")  # HyperOS
    os_part = f"HyperOS {os_name}" if os_name else f"build {t.prop('ro.build.display.id')}"
    region = t.prop("ro.miui.region") or t.prop("ro.product.locale")
    print(f"# {name} ({t.prop('ro.product.model')}, {t.prop('ro.product.device')}, "
          f"{t.prop('ro.product.name')}), {os_part}, Android {t.prop('ro.build.version.release')} "
          f"(SDK {t.prop('ro.build.version.sdk')}), region {region}")
    guide = maker_guide(maker)
    if guide:  # stderr, so `$(pad.py probe)` still captures only the header line
        print(f"Setup notes for {maker} devices: {guide.relative_to(ROOT)}", file=sys.stderr)


def maker_guide(maker):
    """docs/<maker>.md for this manufacturer (Redmi and POCO report Xiaomi), if there is one."""
    name = re.sub(r"[^a-z0-9]+", "-", (maker or "").lower()).strip("-")
    guide = ROOT / "docs" / f"{name}.md"
    return guide if name and guide.is_file() else None


def cmd_backup(t, args):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(args.dir or Path("backups") / f"{safe_name(t.serial)}-{stamp}")
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "packages-all.txt": "pm list packages -u",
        "packages-installed.txt": "pm list packages",
        "packages-system.txt": "pm list packages -s",
        "packages-user.txt": "pm list packages -3",
        "packages-disabled.txt": "pm list packages -d",
        "getprop.txt": "getprop",
        "settings-global.txt": "settings list global",
        "settings-secure.txt": "settings list secure",
        "settings-system.txt": "settings list system",
        "home.txt": "cmd package resolve-activity --brief -a android.intent.action.MAIN "
                    "-c android.intent.category.HOME",
    }
    for name, command in files.items():
        text = t.sh(command, check=False)
        if name.startswith("packages-"):
            text = "".join(sorted(text.splitlines(keepends=True)))
        (out / name).write_text(text, encoding="utf-8")
    print(f"backup written to {out}/")


def cmd_scaffold(t, args):
    rules = protected_rules()
    states = t.states()
    known, optional = {}, {}  # package -> first device folder that lists it
    for f in device_lists():
        for p in read_list(f):
            known.setdefault(p, f.parent.name)
        for p in read_optional(f):
            optional.setdefault(p, f.parent.name)
    noise = re.compile(r"(overlay|auto_generated_rro|\.res$|resources)", re.I)
    present = sorted(p for p, s in states.items() if s != "removed")
    from_lists = [p for p in present if p in known and not is_protected(p, rules)]
    opt = [p for p in present if p in optional and p not in known and not is_protected(p, rules)]
    unreviewed = [p for p in present if p not in known and p not in optional
                  and not is_protected(p, rules) and not noise.search(p)]
    lines = []
    if args.header:
        lines.append(args.header)
    lines += ["# Draft from tools/pad.py scaffold: review every line before running disable.",
              "# Apply:  tools/pad.py disable <this file>",
              "# Undo:   tools/pad.py restore <this file>",
              "",
              "# Listed for other tablets (check each still makes sense here)"]
    lines += [f"{p:<56}# {known[p]}" + (" (already disabled)" if states[p] == "disabled" else "")
              for p in from_lists]
    lines += ["", "# Optional: apps other lists leave to the owner. Uncomment the ones you don't use.",
              *[f"# {p:<54}# {optional[p]}" for p in opt]]
    lines += ["", "# UNREVIEWED: not in any list yet. Look at each with `adb shell dumpsys package <name>`,",
              "# uncomment what is safe to disable and move it into a group with a comment.",
              *[f"# {p}" for p in unreviewed]]
    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"draft written to {args.out}: {len(from_lists)} known, {len(opt)} optional, {len(unreviewed)} unreviewed")
    else:
        sys.stdout.write(text)


def cmd_diff(t, args):
    states = t.states()
    for p in read_list(args.list):
        s = states.get(p, "missing")
        mark = {"enabled": " ", "disabled": "-", "removed": "x", "missing": "?"}[s]
        print(f"{mark} {p:<56}{s}")


def check_protected(names, force):
    rules = protected_rules()
    hit = [p for p in names if is_protected(p, rules)]
    if hit and not force:
        raise PadError("refusing: these are in protected/ and can break the tablet "
                       "(--force to override):\n  " + "\n  ".join(hit))
    return hit


def error_line(out):
    """The useful line of a pm failure: the exception message, not the last stack frame."""
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    return next((l for l in lines if "Exception:" in l or l.startswith("Failure")), lines[0] if lines else "")


def ok_disabled(out):
    return "new state: disabled" in out


def ok_success(out):
    return out.strip().startswith("Success") or "\nSuccess" in out


def cmd_disable(t, args):
    names = read_list(args.list)
    check_protected(names, args.force)
    states = t.states()
    path = record_path(t.serial, args.list)
    record = load_json(path) or {"version": VERSION, "serial": t.serial,
                                 "list": str(Path(args.list).resolve()),
                                 "created": datetime.datetime.now().isoformat(timespec="seconds"),
                                 "packages": {}}
    # The first record of a package wins: a retry after a half-applied list must not record the
    # half-broken state as the original.
    for p in names:
        record["packages"].setdefault(p, {"before": states.get(p, "missing"), "method": None})
    if args.dry_run:
        for p in names:
            print(f"would {'disable' if states.get(p) == 'enabled' else 'skip'}: {p} ({states.get(p, 'missing')})")
        return
    # Saved before the first command reaches the tablet: if this fails, nothing has been changed.
    save_json(path, record)

    done = skipped = failed = 0
    for p in names:
        s = states.get(p, "missing")
        if s != "enabled":
            print(f"  skip      {p} ({s})")
            skipped += 1
            continue
        out = t.sh(f"pm disable-user --user 0 {p}")
        if ok_disabled(out):
            method = "disable"
        else:
            # HyperOS refuses disable-user for every preinstalled system app ("Cannot disable system
            # packages"); removing it for user 0 keeps the APK on the system partition, and
            # install-existing brings it back.
            out2 = t.sh(f"pm uninstall -k --user 0 {p}")
            method = "uninstall" if ok_success(out2) else None
            if not method:
                print(f"  FAILED    {p}: {error_line(out2) or error_line(out)}")
                failed += 1
                continue
        record["packages"][p]["method"] = method
        save_json(path, record)
        print(f"  {method:<9} {p}")
        done += 1
        if args.limit and done >= args.limit:
            print(f"stopped after {done} (--limit); run the same command again to continue")
            break
        if args.batch and done % args.batch == 0 and p != names[-1]:
            try:
                answer = input(f"{done} changed. Check the tablet, then Enter to go on or q to stop: ")
            except EOFError:
                answer = ""
            if answer.strip().lower().startswith("q"):
                break
    print(f"{done} changed, {skipped} skipped, {failed} failed. Record: {path}")
    print(f"Undo: tools/pad.py restore {args.list}")


def restore_one(t, p, method):
    if method == "uninstall":
        return t.sh(f"cmd package install-existing --user 0 {p}")
    return t.sh(f"pm enable --user 0 {p}")


def cmd_restore(t, args):
    names = read_list(args.list)
    path = record_path(t.serial, args.list)
    record = load_json(path)
    states = t.states()
    plan = []
    if record is None:
        print(f"warning: no record at {path}; bringing back every package in the list", file=sys.stderr)
        for p in names:
            if states.get(p) in ("disabled", "removed"):
                plan.append((p, "uninstall" if states[p] == "removed" else "disable"))
    else:
        for p in names:
            entry = record["packages"].get(p)
            if not entry:
                continue  # added to the list after the last disable run; never changed by it
            if entry["before"] != "enabled":
                if entry["before"] != "missing":
                    print(f"  leave     {p} (already {entry['before']} before this list)")
                continue
            now = states.get(p)
            if now == "removed":
                plan.append((p, "uninstall"))
            elif now == "disabled":
                plan.append((p, "disable"))
    for p, method in plan:
        if args.dry_run:
            print(f"would restore {p} ({method})")
            continue
        out = restore_one(t, p, method)
        # install-existing leaves a package enabled; a package disabled earlier needs enabling too.
        if method == "uninstall" and p in t.packages("-d"):
            out = t.sh(f"pm enable --user 0 {p}")
        print(f"  restored  {p}: {out.strip().splitlines()[-1] if out.strip() else 'ok'}")
    if not plan:
        print("nothing to restore")


def cmd_tweak(t, args):
    path = state_dir(t.serial) / "tweaks.json"
    saved = load_json(path) or {}
    if args.undo:
        before = saved.get(args.name)
        if not before:
            raise PadError(f"no saved values for {args.name}; nothing to undo")
        for ns, key, _ in TWEAKS[args.name]:
            t.put_setting(ns, key, before[f"{ns}/{key}"])
            print(f"  {ns} {key} -> {before[f'{ns}/{key}']}")
        del saved[args.name]
        save_json(path, saved)
        return
    if args.name not in saved:  # first value wins, so applying twice still undoes to the original
        before = {f"{ns}/{key}": t.get_setting(ns, key) for ns, key, _ in TWEAKS[args.name]}
        for v in before.values():
            if not SETTING_RE.match(v):
                raise PadError(f"unexpected setting value {v!r}; not touching anything")
        saved[args.name] = before
        save_json(path, saved)
    for ns, key, value in TWEAKS[args.name]:
        t.put_setting(ns, key, value)
        print(f"  {ns} {key} = {value}")
    print(f"Undo: tools/pad.py tweak {args.name} --undo")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pad.py", description=__doc__.split("\n")[0])
    ap.add_argument("-s", "--serial", help="adb serial (default: $PAD_SERIAL or the only device)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe")
    b = sub.add_parser("backup"); b.add_argument("dir", nargs="?")
    s = sub.add_parser("scaffold"); s.add_argument("--out"); s.add_argument("--header")
    d = sub.add_parser("diff"); d.add_argument("list")
    x = sub.add_parser("disable"); x.add_argument("list")
    x.add_argument("--batch", type=int, default=0, help="pause after every N changes")
    x.add_argument("--limit", type=int, default=0, help="stop after N changes; run again to continue")
    x.add_argument("--dry-run", action="store_true"); x.add_argument("--force", action="store_true")
    r = sub.add_parser("restore"); r.add_argument("list"); r.add_argument("--dry-run", action="store_true")
    tw = sub.add_parser("tweak"); tw.add_argument("name", choices=sorted(TWEAKS))
    tw.add_argument("--undo", action="store_true")
    args = ap.parse_args(argv)
    try:
        # Lists are checked before anything connects, so a bad one never reaches the tablet.
        if getattr(args, "list", None):
            names = read_list(args.list)
            if args.cmd == "disable":
                check_protected(names, args.force)
        t = Tablet(args.serial)
        globals()[f"cmd_{args.cmd}"](t, args)
    except PadError as e:
        print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
