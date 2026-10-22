"""A stand-in for `adb` that keeps a pretend tablet in a JSON file ($FAKE_ADB_STATE).

State: {"packages": {name: "enabled" | "disabled" | "removed"}, "refuse_disable": [names],
        "settings": {"global/key": value}, "props": {name: value}, "log": [shell commands]}
"""
import json
import os
import sys

path = os.environ["FAKE_ADB_STATE"]
with open(path) as f:
    st = json.load(f)
args = sys.argv[1:]

if args == ["devices"]:
    print("List of devices attached")
    for serial in st.get("devices", ["fake-tablet"]):
        print(f"{serial}\tdevice")
    sys.exit(0)

assert args[0] == "-s" and args[2] == "shell", args
cmd = args[3]
st.setdefault("log", []).append(cmd)
w = cmd.split()
pk = st["packages"]
out = ""

if w[:3] == ["pm", "list", "packages"]:
    flag = w[3] if len(w) > 3 else ""
    names = [p for p, s in pk.items()
             if flag == "-u" or (flag == "-d" and s == "disabled") or (flag in ("", "-s", "-3") and s != "removed")]
    out = "".join(f"package:{p}\n" for p in sorted(names))
elif w[:2] == ["pm", "disable-user"]:
    p = w[-1]
    if p not in pk or pk[p] == "removed":
        out = f"Exception occurred while executing 'disable-user':\njava.lang.IllegalArgumentException: Unknown package: {p}\n"
    elif p in st.get("refuse_disable", []):
        out = f"Exception occurred while executing 'disable-user':\njava.lang.SecurityException: Cannot disable a protected package: {p}\n"
    else:
        pk[p] = "disabled"
        out = f"Package {p} new state: disabled-user\n"
elif w[:2] == ["pm", "uninstall"]:
    pk[w[-1]] = "removed"
    out = "Success\n"
elif w[:2] == ["pm", "enable"]:
    pk[w[-1]] = "enabled"
    out = f"Package {w[-1]} new state: enabled\n"
elif w[:3] == ["cmd", "package", "install-existing"]:
    p = w[-1]
    if pk.get(p) == "removed":
        pk[p] = "enabled"
    out = f"Package {p} installed for user: 0\n"
elif w[0] == "getprop":
    out = st.get("props", {}).get(w[1], "") + "\n" if len(w) > 1 else ""
elif w[:2] == ["settings", "get"]:
    out = st.get("settings", {}).get(f"{w[2]}/{w[3]}", "null") + "\n"
elif w[:2] == ["settings", "put"]:
    st.setdefault("settings", {})[f"{w[2]}/{w[3]}"] = w[4]
elif w[:2] == ["settings", "delete"]:
    st.get("settings", {}).pop(f"{w[2]}/{w[3]}", None)

with open(path, "w") as f:
    json.dump(st, f)
sys.stdout.write(out)
