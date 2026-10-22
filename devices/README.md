# Devices

One folder per tablet model, each with a `debloat.txt` listing the packages that are safe to disable
on that firmware, grouped and commented. These are starting points: comment out anything you use.
Lines like `# com.example.app` are optional extras you uncomment yourself.

To start a list for a tablet that isn't here, connect it and run
`tools/pad.py scaffold --header "$(tools/pad.py probe)" --out devices/<brand>-<model>/debloat.txt`.

| Folder | Tablet | OS | Notes |
|---|---|---|---|
| `xiaomi-redmi-pad-2-pro/` | Xiaomi Redmi Pad 2 Pro (25099RP13G, flute), EEA | HyperOS 3.0 / Android 16 | Xiaomi telemetry (analytics, MiSight, Mi Feedback), MSA ad engine, Cleaner, Google setup leftovers and Privacy Sandbox, Qualcomm debug tools, carrier presets; Xiaomi and Google apps optional; joyose, daemon, miservice, Cloud, Find Device, pen and keyboard services kept |
