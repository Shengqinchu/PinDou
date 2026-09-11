"""Install the selected-user Mac worker. Read its private deployment bundle on stdin.

Run using launchctl asuser with the paired user's credentials. This installs only
PinDou's worker/guard in that user's Application Support and LaunchAgents folders.
It does not modify Apple accounts, TCC grants, or other users' services.
"""
import json
import os
import plistlib
import pwd
import shlex
import subprocess
import sys
from pathlib import Path


def main():
    if sys.platform != "darwin":
        raise SystemExit("macOS required")
    value = json.load(sys.stdin)
    config = value["config"]
    user = pwd.getpwuid(os.getuid()).pw_name
    if user != config["user"] or user not in ("chix", "pindou_sms"):
        raise SystemExit("paired user required")
    if config["role"] not in ("customer", "owner_alert"):
        raise SystemExit("invalid role")
    os.umask(0o077)
    base = Path.home() / "Library/Application Support/PinDouSMS/message-bridge"
    base.mkdir(parents=True, exist_ok=True)
    base.chmod(0o700)
    worker, settings = base / "worker.py", base / "config.json"
    compile(value["worker"], str(worker), "exec")
    for path, body in [(worker, value["worker"]), (settings, json.dumps(config))]:
        temporary = path.with_suffix(path.suffix + ".next")
        temporary.write_text(body, encoding="utf-8")
        temporary.chmod(0o600)
        temporary.replace(path)
    launcher = base / "PinDou Messages.command"
    launcher.write_text("#!/bin/zsh\nexec /usr/bin/python3 " + shlex.quote(str(worker)) + " --config " + shlex.quote(str(settings)) + "\n", encoding="utf-8")
    launcher.chmod(0o700)
    guard = base / "guard.py"
    guard.write_text('''import fcntl,subprocess
from pathlib import Path
base=Path(__file__).resolve().parent
with (base/'worker.lock').open('a') as handle:
 try: fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError: raise SystemExit(0)
 # Release before the worker starts. The worker takes the same exclusive lock.
 fcntl.flock(handle,fcntl.LOCK_UN)
subprocess.run(['/usr/bin/open','-g','-n','-a','Terminal',str(base/'PinDou Messages.command')],check=True)
''', encoding="utf-8")
    guard.chmod(0o600)
    label = "com.pindou.messages." + config["role"]
    agents = Path.home() / "Library/LaunchAgents"
    agents.mkdir(exist_ok=True)
    agent = agents / (label + ".plist")
    agent.write_bytes(plistlib.dumps({"Label": label, "ProgramArguments": ["/usr/bin/python3", str(guard)],
        "RunAtLoad": True, "StartInterval": 60, "ProcessType": "Background",
        "StandardOutPath": str(base / "guard.log"), "StandardErrorPath": str(base / "guard.log")}))
    agent.chmod(0o600)
    target = "gui/" + str(os.getuid())
    check = subprocess.run(["/bin/launchctl", "print", target + "/" + label], capture_output=True)
    if check.returncode == 0:
        subprocess.run(["/bin/launchctl", "bootout", target + "/" + label], check=True, capture_output=True)
    subprocess.run(["/bin/launchctl", "bootstrap", target, str(agent)], check=True, capture_output=True)
    print(json.dumps({"installed": True, "user": user, "role": config["role"], "send_enabled_locally": config["allow_send"]}))


if __name__ == "__main__":
    main()
