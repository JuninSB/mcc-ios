"""Create an Alpine apkovl for automatic, local x86 validation under QEMU.

The archive is guest configuration, never applied to the host. Serve it alongside
a git archive named mcc-ish-source.tar on the host's loopback HTTP server.
"""
import argparse
import io
import tarfile

parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
parser.add_argument('--startup-script', help='Use an explicit guest-only startup script instead of the MCC suite')
args = parser.parse_args()

startup = b'''#!/bin/sh
set -eu
exec > /dev/ttyS0 2>&1
trap 'echo MCC_ALPINE_EXIT=$?' EXIT
echo MCC_ALPINE_TEST_START
uname -m
apk --print-arch
cat /etc/alpine-release
ip link set lo up
ip addr replace 127.0.0.1/8 dev lo
printf '%s\n' 'https://dl-cdn.alpinelinux.org/alpine/v3.22/main' 'https://dl-cdn.alpinelinux.org/alpine/v3.22/community' > /etc/apk/repositories
mkdir -p /root/mcc-test
wget -q http://10.0.2.2:8766/mcc-ish-source.tar -O /tmp/mcc-source.tar
tar -xf /tmp/mcc-source.tar -C /root/mcc-test
cd /root/mcc-test
sh install.sh
mono --version
sh run.sh --help
apk add --no-progress openssl
python3 tests/ish_network.py ports/ish/MinecraftClient/bin/Release/MinecraftClient.exe --mono --threshold 0
python3 tests/ish_network.py ports/ish/MinecraftClient/bin/Release/MinecraftClient.exe --mono --finish truncated
mcs -sdk:4 -r:ports/ish/MinecraftClient/bin/Release/MinecraftClient.exe -out:ports/ish/MinecraftClient/bin/Release/IshCrypto.exe tests/ish-crypto/Program.cs
python3 tests/ish_crypto.py ports/ish/MinecraftClient/bin/Release/IshCrypto.exe --mono
mono ports/ish/MinecraftClient/bin/Release/IshCrypto.exe --configuration
mono ports/ish/MinecraftClient/bin/Release/IshCrypto.exe --network-text
mono ports/ish/MinecraftClient/bin/Release/IshCrypto.exe --modern-login
mono ports/ish/MinecraftClient/bin/Release/IshCrypto.exe --timeout-failure
python3 tests/ish_modern_session.py ports/ish/MinecraftClient/bin/Release/IshCrypto.exe --mono
python3 tests/ish_auth.py ports/ish/MinecraftClient/bin/Release/MinecraftClient.exe --mono
echo MCC_ALPINE_TEST_PASS
'''

if args.startup_script:
    from pathlib import Path
    startup = Path(args.startup_script).read_bytes().replace(b'\r\n', b'\n')
    if not startup.startswith(b'#!/bin/sh\n'):
        parser.error('startup script must begin with #!/bin/sh')

with tarfile.open(args.output, 'w:gz') as archive:
    entry = tarfile.TarInfo('etc/local.d/mcc.start')
    entry.mode = 0o755
    entry.size = len(startup)
    archive.addfile(entry, io.BytesIO(startup))
    entry = tarfile.TarInfo('etc/runlevels/default/local')
    entry.type = tarfile.SYMTYPE
    entry.linkname = '/etc/init.d/local'
    archive.addfile(entry)
print(args.output)
