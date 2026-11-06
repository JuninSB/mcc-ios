"""Explicit offline-mode integration against a user-controlled Paper; exercises the main MCC entry point."""
import argparse
import pathlib
import queue
import subprocess
import tempfile
import threading
import time

parser = argparse.ArgumentParser()
parser.add_argument('executable', type=pathlib.Path)
parser.add_argument('--host', required=True)
parser.add_argument('--port', type=int, default=25565)
parser.add_argument('--offline-test', action='store_true', required=True)
parser.add_argument('--mono', action='store_true')
args = parser.parse_args()
with tempfile.TemporaryDirectory(prefix='mcc-modern-console-') as state:
    config = pathlib.Path(state, 'test.ini')
    config.write_text(f'[Main]\nlogin=PortTest\npassword=-\nserverip={args.host}:{args.port}\nmcversion=1.21.11\nconsoletitle=\nsessioncache=none\nminecraftrealms=false\n')
    command = (['mono'] if args.mono else []) + [str(args.executable.resolve()), str(config), 'BasicIO-NoColor']
    child = subprocess.Popen(command, cwd=state, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    lines, events = [], queue.Queue()
    def capture():
        for line in child.stdout:
            lines.append(line)
            events.put(line)
    reader = threading.Thread(target=capture, daemon=True)
    reader.start()
    try:
        sent = replied = echoed = False
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline and child.poll() is None:
            try:
                line = events.get(timeout=0.2)
            except queue.Empty:
                continue
            if 'Joined the 1.21.11 server' in line and not sent:
                child.stdin.write('/version\n')
                child.stdin.flush()
                sent = True
            if sent and not replied and 'Paper' in line and '1.21.11' in line:
                replied = True
                child.stdin.write('MCC_ISH_CHAT_ROUNDTRIP\n')
                child.stdin.flush()
            if replied and 'MCC_ISH_CHAT_ROUNDTRIP' in line:
                echoed = True
                child.stdin.write('/exit\n')
                child.stdin.flush()
                break
        assert sent and replied and echoed, ''.join(lines)
        child.wait(timeout=10)
        reader.join(timeout=2)
        assert child.returncode == 0, (child.returncode, ''.join(lines))
        print('PASS: main MCC executable, INI, 774 join, /version, real player-chat roundtrip, /exit and status zero.')
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
        print(''.join(lines))
