# CleanYourTablet

Strip the bloatware, telemetry and ad services from an Android tablet over Wi-Fi. **No root, no
unlocked bootloader, nothing removed from the system partition, and a one-line restore.** Started
on a Xiaomi Redmi Pad 2 Pro running HyperOS 3; one folder per model, so anyone can add theirs.

Inspired by [CleanYourTV](https://github.com/Gathin23/cleanyourtv), which does the same for
Android TVs.

## How it works

Tablets have the same debug bridge as phones and TVs. Switch on Wireless debugging, pair your
computer once, and the rest is standard Android tooling:

1. **Back up** the package list and settings.
2. **Disable** the manufacturer's telemetry, ad engine and preloaded junk with `pm disable-user`.
   Where HyperOS refuses to disable one of its own packages, it is removed for your user only
   (`pm uninstall -k --user 0`); the APK stays on the system and `restore` brings it back.
3. **Optionally** switch on ad-blocking Private DNS and faster animations, and turn off the ad
   toggles hidden inside Xiaomi's apps.

Every change is recorded before it happens, so `restore` puts back exactly what was there,
including apps you had already disabled yourself.

## Quick start

You need a computer on the same Wi-Fi as the tablet, [Android platform-tools](https://developer.android.com/tools/releases/platform-tools)
(`adb`) and Python 3.8+. No other dependencies.

| | |
|---|---|
| **1. On the tablet** | Settings → About tablet → tap **OS version** seven times. Then Settings → Additional settings → Developer options → **Wireless debugging** on. On Xiaomi, if disabling fails with a `SecurityException`, also turn on **USB debugging (Security settings)**; `pad.py` falls back to removing the package for your user anyway. |
| **2. Pair** | In Wireless debugging, tap **Pair device with pairing code**, then on the computer: `adb pair <ip>:<pairing port>` and `adb connect <ip>:<port>` (the second port is shown on the Wireless debugging screen). |
| **3. Debloat** | `tools/pad.py backup` → `tools/pad.py diff devices/<your tablet>/debloat.txt` → edit the list → `tools/pad.py disable devices/<your tablet>/debloat.txt --batch 10` |

Or let an AI assistant do it: paste [`PROMPT.md`](PROMPT.md) into Claude Code (or another coding
assistant with shell access) in a clone of this repo. It backs up, sorts the packages, asks you
which apps you use, disables in small batches and checks the tablet with screenshots.

Undo everything: `tools/pad.py restore devices/<your tablet>/debloat.txt`.
Undo one app: Settings → Apps → the app → Enable, or `adb shell pm enable --user 0 <package>`
(for removed ones, `adb shell cmd package install-existing <package>`).

## Commands

| Command | |
|---|---|
| `tools/pad.py probe` | The header line for a new list: model, codename, OS build, Android version, region |
| `tools/pad.py backup [dir]` | Package lists, `getprop`, all settings and the Home app into `backups/` |
| `tools/pad.py scaffold --out FILE` | A draft list for a new tablet, built from every list in `devices/` |
| `tools/pad.py diff LIST` | Which packages in a list are enabled, disabled, removed or missing here |
| `tools/pad.py disable LIST [--batch N] [--dry-run]` | Disable (or remove for user 0) every package in the list |
| `tools/pad.py restore LIST` | Undo `disable`, from its record in `~/.cleanyourtablet/` |
| `tools/pad.py tweak private-dns\|animations [--undo]` | AdGuard Private DNS (doesn't block YouTube ads); 0.5x animations |

With several devices connected, pass `--serial` or set `PAD_SERIAL`.

`disable` refuses any list that contains a package from [`protected/`](protected/): things like
the security centre, the HyperOS launcher, Find Device and the pen service, which bootloop the
tablet or break Settings. `--force` overrides it; please don't.

## Supported tablets

Anything running Android 11 or newer with Wireless debugging (older ones work over USB). Tested
lists, one folder per model in [`devices/`](devices/):

| Tablet | OS |
|---|---|
| Xiaomi Redmi Pad 2 Pro (25099RP13G, flute), EEA | HyperOS 3.0 / Android 16 |

Your tablet isn't here? Run the prompt, live with the result for a few days, and send a pull
request. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

- [CleanYourTV](https://github.com/Gathin23/cleanyourtv) (MIT) for the idea, the list format and
  the record-before-you-change approach to restore.
- [Universal Android Debloater Next Generation](https://github.com/Universal-Debloater-Alliance/universal-android-debloater-next-generation)
  and [fadeltd/xiaomi-debloater](https://github.com/fadeltd/xiaomi-debloater) (both GPL-3.0), whose
  package ratings were the research for the protected lists and the first device list. Their text
  is not copied here; the comments in this repo are our own.
- The [XDA HyperOS 2.0 debloating guide](https://xdaforums.com/t/hyperos-2-0-debloating-guide-bloatware-list.4728062/)
  and [XimiTime's list](https://ximitime.com/unnecessary-xiaomi-apps-you-can-safely-remove-46489/).

## Licence

MIT. Use at your own risk: everything here is reversible, but a tablet is still a computer you
can confuse. Back up first.
