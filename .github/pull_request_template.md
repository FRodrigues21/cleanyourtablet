<!-- One or two sentences on what this changes and the tablet it was tried on is plenty. -->

**Tested on:** <!-- model, OS build, Android version (tools/pad.py probe) -->

### If this adds or changes a device list
- [ ] `devices/<brand>-<model>/debloat.txt`, first line from `tools/pad.py probe`
- [ ] Only packages I actually disabled and lived with for a few days; anything I had to re-enable is noted
- [ ] Apps some people use are under an "Optional" heading as `# package` lines
- [ ] A row in `devices/README.md` and one in the README's tablet table
- [ ] Comments are my own, not copied from GPL lists

### If this touches tools/pad.py
- [ ] Tried on a real tablet
- [ ] A test in `tests/test_pad.py`
- [ ] Still standard library only
