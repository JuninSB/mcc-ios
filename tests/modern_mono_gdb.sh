#!/bin/sh
# Diagnostic run only. A gdb exit status is never treated as runtime success.
set -eu
exec > /dev/ttyS0 2>&1
trap 'diagnostic_status=$?; echo MCC_MODERN_GDB_EXIT=$diagnostic_status; poweroff -f' EXIT
echo MCC_MODERN_GDB_START
uname -m
printf '%s\n' 'https://dl-cdn.alpinelinux.org/alpine/v3.22/main' > /etc/apk/repositories
apk add --no-progress gdb
mkdir -p /root/modern-smoke
cd /root/modern-smoke
wget -q http://10.0.2.2:8766/modern-smoke.tar.gz -O modern-smoke.tar.gz
wget -q http://10.0.2.2:8766/modern-smoke.tar.gz.sha256 -O archive.sha256
sha256sum -c archive.sha256
tar -xzf modern-smoke.tar.gz
sha256sum -c SHA256SUMS
export MONO_PATH="$PWD"
export LD_LIBRARY_PATH="$PWD"
timeout 90 gdb --batch -ex 'set pagination off' -ex run -ex 'thread apply all bt' -ex 'info registers' -ex 'info sharedlibrary' --args ./mono-sgen MinimalProbe.dll
echo MCC_MODERN_GDB_DIAGNOSTIC_DONE
