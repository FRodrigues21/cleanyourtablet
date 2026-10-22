# Xiaomi Redmi Pad 2 Pro (flute)

Setup steps are the same as for every Xiaomi device: **[docs/xiaomi.md](../../docs/xiaomi.md)**.
On this tablet:

| | |
|---|---|
| Model | 25099RP13G, codename `flute`, product `flute_eea` (Global/EEA), Snapdragon 7s Gen 3, 6 GB RAM, Wi-Fi only |
| Tested on | HyperOS OS3.0.303.0.WPWEUXM, Android 16, October 2026 |
| Connection | Wireless debugging; found again over mDNS after a reboot, on a new port |
| Debloat | `debloat.txt`: 55 packages off, 42 of them removed for user 0 because HyperOS refused to disable them; reboot fine |
| Installing APKs | Needs a Xiaomi account sign-in for **Install via USB**, then a tap on **Install** on the tablet for each `adb install`. Nuvio and TiviMate installed and ran this way |
| Never touch | the Focus Pen and keyboard services (`com.xiaomi.touchservice`, `com.xiaomi.bluetooth`), already in `protected/` |
