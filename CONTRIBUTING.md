# Contributing

Thanks for helping more tablets lose their ads. The most useful thing you can send is your model.

## Add your tablet

1. Connect it (see the README) and run
   `tools/pad.py scaffold --header "$(tools/pad.py probe)" --out devices/<brand>-<model>/debloat.txt`,
   or start from the list of a close relative in `devices/`. Or run [`PROMPT.md`](PROMPT.md) and let
   your assistant do it.
2. Format, the same as CleanYourTV's: one package per line, grouped under a comment that says what
   the group is, and a trailing comment on anything non-obvious ("re-enable for firmware updates",
   "needed for the pen"). Apps some people use go under an "Optional" heading as `# package` lines.
3. The first line is the output of `tools/pad.py probe`: model name, model number, codename,
   OS build, Android version and region, so people can tell whether it matches theirs.
4. Only list packages you actually disabled and lived with for a few days. Note anything that broke
   and what you re-enabled. Say in the header what you kept on purpose and why.
5. Folder names are lowercase `<brand>-<model>`, e.g. `xiaomi-redmi-pad-2-pro`,
   `samsung-galaxy-tab-s9-fe`, `lenovo-tab-p12`. Different firmware regions of the same model can
   share a folder if the list is the same; otherwise add `-cn`, `-in` and so on.
6. Add a row to `devices/README.md` and one to the README's tablet table.
7. Run `python3 -m unittest discover -s tests -v`.

Never list packages to *uninstall*. Lists are applied with `pm disable-user`, with
`pm uninstall -k --user 0` only as a fallback the tool records, so everything can be undone from
the tablet's Settings or with `restore`.

Don't copy descriptions from UAD-ng or xiaomi-debloater: they're GPL-3.0 and this repo is MIT.
Use them as research and write your own comments.

## Protected packages

If disabling a package bootlooped your tablet, broke Settings, the lock screen, notifications or
the pen, add it to `protected/android.txt` (any Android) or `protected/<maker>-<os>.txt` with a
comment saying what broke and on which model. That stops `pad.py disable` from ever applying it.

## Improve the tool

`tools/pad.py` is deliberately one file and uses only the Python standard library plus the `adb`
binary. Keep it that way. Every package name that reaches the tablet's shell is checked against a
strict regex first; keep that too. New behaviour needs a test in `tests/test_pad.py`, which runs
against `tests/fake_adb.py` instead of a real tablet.
