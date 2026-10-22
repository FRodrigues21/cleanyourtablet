# Xiaomi, Redmi and POCO (HyperOS)

Setup notes for every tablet with `ro.product.manufacturer=Xiaomi`; `tools/pad.py probe` points
here when it sees one. Checked on a Redmi Pad 2 Pro with HyperOS 3.0 (Android 16). Menu names are
from the English UI; on HyperOS 2 some items sit one level higher.

## 1. Developer options

Settings → About tablet → tap **OS version** seven times. Developer options then appear under
Settings → Additional settings → Developer options.

## 2. Wireless debugging

Developer options → **Wireless debugging** on → **Pair device with pairing code**, then on the
computer:

```sh
adb pair <ip>:<pairing port>     # enter the six-digit code
adb connect <ip>:<port>          # the port shown on the Wireless debugging screen
```

After the first pairing, `adb devices` usually finds the tablet by itself over mDNS (a serial like
`adb-<id>._adb-tls-connect._tcp`). The port changes after every reboot and every time Wireless
debugging or Wi-Fi is switched off and on, so don't save it anywhere. If a script needs it,
`adb mdns services` shows the current one.

## 3. Sign in to a Xiaomi account (only needed to install apps)

HyperOS has two extra switches in Developer options that **only turn on while you are signed in
to a Xiaomi account** (Settings → Xiaomi account):

| Switch | Without it |
|---|---|
| **Install via USB** | `adb install` fails with `INSTALL_FAILED_USER_RESTRICTED: Install canceled by user`. Wireless debugging counts as "USB" here. |
| **USB debugging (Security settings)** | On MIUI this was needed for adb to grant permissions and simulate taps. Not needed for anything in this repo so far (key events worked without it); untested on HyperOS 3. |

Even with **Install via USB** on, every `adb install` shows an install prompt on the tablet, and
you have to tap **Install** on the tablet before the command returns. Keep the screen on and
unlocked while installing.

**You don't need the account to debloat.** These worked on a tablet that wasn't signed in:
`tools/pad.py` backup, disable and restore, screenshots (`adb exec-out screencap -p`), key events
(`input keyevent`), and opening the notification shade (`cmd statusbar`).

No account and need to install an APK? Copy it to the tablet and install it there:

```sh
adb push app.apk /sdcard/Download/
```

Then File Manager → Downloads → tap the APK, and allow installs from File Manager when HyperOS asks.

## 4. What to expect when debloating

- HyperOS refuses `pm disable-user` for every preinstalled system app
  (`SecurityException: Cannot disable system packages`). `tools/pad.py disable` then removes the
  app for your user (`pm uninstall -k --user 0`) and records this, and `restore` brings it back
  with `cmd package install-existing`. Apps that Xiaomi updates through the store (Notes, Weather,
  Calculator...) disable normally.
- `protected/xiaomi-hyperos.txt` lists the packages that bootloop HyperOS or break Settings, the
  lock screen, notifications or the pen. `pad.py` won't touch them.

## 5. Ad switches inside Xiaomi apps

There is no adb setting for these, so turn them off by hand. Search Settings if a path doesn't
match your version.

- Settings → Passwords & security → Authorisation & revocation → **msa** off. This is skipped if
  your list already removed `com.miui.msa.global`.
- Settings → Passwords & security → Privacy → Ad services → **Personalised ads** off.
- **Receive recommendations** off in the settings of Security, Downloads, File Manager, Themes and
  GetApps.
- Lock screen → Wallpaper Carousel / Glance off.

## When you're done

Switch Wireless debugging off. You can also switch off Install via USB and USB debugging
(Security settings), and sign out of the Xiaomi account if you only signed in for this.
