#!/bin/sh
# Minimal managed execution probe, not a complete MCC/runtime validation.
set -eu
exec > /dev/ttyS0 2>&1
trap 'smoke_status=$?; echo MCC_MODERN_SMOKE_EXIT=$smoke_status; poweroff -f' EXIT
echo MCC_MODERN_SMOKE_START
uname -m
apk --print-arch
cat /etc/alpine-release
mkdir -p /root/modern-smoke
cd /root/modern-smoke
wget -q http://10.0.2.2:8766/modern-smoke.tar.gz -O modern-smoke.tar.gz
wget -q http://10.0.2.2:8766/modern-smoke.tar.gz.sha256 -O archive.sha256
sha256sum -c archive.sha256
tar -xzf modern-smoke.tar.gz
sha256sum -c SHA256SUMS
export MONO_PATH="$PWD"
export LD_LIBRARY_PATH="$PWD"
timeout 15 ./mono-sgen --version
probe_status=0
timeout 30 ./mono-sgen MinimalProbe.dll || probe_status=$?
echo MCC_MODERN_MANAGED_PROBE_EXIT=$probe_status
test "$probe_status" -eq 73
echo MCC_MODERN_SMOKE_PASS
