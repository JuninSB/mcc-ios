#!/bin/sh
set -u
uname -a
cat /etc/alpine-release 2>/dev/null
if [ -d /proc/ish ]; then echo 'iSH /proc interface present'; fi
for tool in apk mono xbuild; do
    command -v "$tool" || exit 69
done
apk --print-arch
mono --version
mono --help >/dev/null || exit 70
echo 'Runtime starts. This does not verify MCC login or server connectivity.'
