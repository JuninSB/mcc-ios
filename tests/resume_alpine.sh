#!/bin/sh
# Run from the source root after install.sh completed in Alpine x86.
set -eu
trap 'echo MCC_ALPINE_RESUME_EXIT=$?' EXIT
echo MCC_ALPINE_RESUME_START
ip link set lo up
ip addr replace 127.0.0.1/8 dev lo
mono --version
env -u HOME sh run.sh --help
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
