# The prompt

Paste this into Claude Code (or another coding assistant with shell access) on a computer on the
same Wi-Fi as the tablet. Run it from a clone of this repo so the assistant uses `tools/pad.py`
and the lists in `devices/` instead of writing its own.

Before you start, on the tablet: Settings → About tablet → tap the OS/Build version 7 times, then
Developer options → turn on **Wireless debugging**. On Xiaomi, also turn on **USB debugging
(Security settings)** if you can (it needs a Mi account); it lets the assistant send taps and key
presses to check its work.

---

I want to debloat my Android tablet: remove the manufacturer's telemetry, ads and preloaded apps I
don't use, without root and reversibly. My tablet is: <MODEL NAME HERE>. This repo has the tools
(`tools/pad.py`) and tested lists (`devices/`). Work on the real device, step by step, and check
what you do with screenshots from the tablet (`adb exec-out screencap -p > s.png`). Ask me before
anything that depends on how I use the tablet.

Connect
- Check `adb devices` first: the tablet may already be connected over mDNS. If not, ask me for the
  IP and pairing code and port from Developer options > Wireless debugging > Pair device with
  pairing code, then run `adb pair <ip>:<pairing port>` and `adb connect <ip>:<port>`. The connect
  port is different from the pairing port, and both change whenever Wireless debugging is toggled or
  Wi-Fi drops; `adb mdns services` shows the current one.
- If `adb` says "No route to host" on macOS although the tablet is reachable, macOS Local Network
  privacy is blocking the terminal: tell me to allow it in System Settings > Privacy & Security >
  Local Network.

Back up first
- Run `tools/pad.py probe` and `tools/pad.py backup`. Show me the probe line.
- If `devices/` has a folder for my model, start from its `debloat.txt` (`tools/pad.py diff` shows
  what applies). If not, make a draft with `tools/pad.py scaffold --header "$(tools/pad.py probe)"
  --out devices/<brand>-<model>/debloat.txt`. Lists for other tablets from the same maker and OS
  are good evidence; similar phone lists less so.

Sort the packages
- Group what's left into: manufacturer telemetry and diagnostics, ad services, background
  services I probably don't need (cleaners, duplicate share/cast, carrier presets), setup-only
  leftovers, preloaded apps, and Google apps.
- For every package you're not sure about, check its activities, services, `codePath` and
  `sharedUser` with `adb shell dumpsys package <name>` before deciding. A package running as
  `android.uid.system` with no clear purpose stays enabled. Say so in a comment.
- Never touch anything in `protected/` (`pad.py disable` refuses it anyway). On tablets also keep:
  the stylus and keyboard services, the camera, the stock launcher (HyperOS turns off gesture
  navigation with third-party launchers), Find Device, the cloud account, push services, the
  file manager unless I've installed another.
- Before disabling any app I might use (browser, music, video, notes, weather, calculator, Gmail,
  YouTube, Maps, Photos, Drive, Calendar, the assistant, Xiaomi Home, the voice hotword,
  accessibility tools), ask me with a checklist question and disable only what I tick. Put the
  ones I keep under an "Optional" heading as `# package` lines, so other people can choose.

Disable
- `tools/pad.py disable <list> --dry-run` first and show me the summary.
- Then run `tools/pad.py disable <list> --limit 8` repeatedly (each run carries on where the last
  stopped; `--batch` is the same for a person at a keyboard). After each batch: take a screenshot of the home
  screen, pull down the notification shade, open Settings. If anything misbehaves, stop, re-enable
  the batch one package at a time (`adb shell pm enable --user 0 <pkg>`, or
  `adb shell cmd package install-existing <pkg>` if it was removed) to find the culprit, move it out
  of the list with a comment saying why, and carry on.
- At the end, reboot (`adb reboot`), wait, reconnect and check again: lock screen, unlock,
  notifications, Wi-Fi, Bluetooth, camera, Play Store, and the pen and keyboard if I have them.

Tweaks (ask first, all optional)
- Ad-blocking DNS: `tools/pad.py tweak private-dns`. Tell me it doesn't block YouTube ads, and check
  that an app still loads afterwards. Undo: `tools/pad.py tweak private-dns --undo`.
- Faster animations: `tools/pad.py tweak animations`.
- On Xiaomi, walk me through the in-app ad switches, which have no adb setting (menu names move
  between HyperOS versions, so search Settings if a path doesn't match): revoke MSA under
  Settings > Passwords & security > Authorisation & revocation (skip this if MSA is already disabled); Settings > Passwords & security > Privacy >
  Ad services > Personalised ads off; and "Receive recommendations" off in Security, Downloads, File
  Manager, Themes and GetApps settings, plus lock screen Glance / Wallpaper Carousel off.

Finish
- Tell me how to undo everything (`tools/pad.py restore <list>`) and how to bring back one app.
- Turn Wireless debugging off when we're done (Android also turns it off when Wi-Fi drops). Remind
  me that USB debugging (Security settings) can be switched off too.
- If this is a new model, or the list changed: make sure the first line is the probe line, every
  group has a comment, nothing I re-enabled is still listed, add a row to `devices/README.md` and
  the README's tablet table, run `python3 -m unittest discover -s tests`, and offer to open a pull
  request once I've used the tablet like this for a few days.

---

Expect two or three checklist questions (which apps you use, whether to keep the assistant and
voice hotword, and the optional tweaks). Everything is reversible.
