# Security

Wireless debugging gives a full shell to any computer you have paired. Turn it off when you're done
(Developer options > Wireless debugging), and revoke old pairings under Developer options > Revoke
USB debugging authorisations. Android also switches Wireless debugging off when Wi-Fi drops.

`tools/pad.py` passes package names from lists into the tablet's shell. It refuses a whole list if
any line is not a bare package name, before connecting. If you find a way around that check, or
anything else that lets a list or a tablet run commands it shouldn't, please report it privately
through GitHub's "Report a vulnerability" on this repository instead of opening an issue.
