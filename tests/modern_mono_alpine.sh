#!/bin/sh
# Guest-only script, invoked through the QEMU apkovl test harness.
set -eu
exec > /dev/ttyS0 2>&1
trap 'echo MCC_MODERN_MONO_EXIT=$?' EXIT
echo MCC_MODERN_MONO_START
uname -m
apk --print-arch
cat /etc/alpine-release
printf '%s\n' \
    'https://dl-cdn.alpinelinux.org/alpine/v3.22/main' \
    'https://dl-cdn.alpinelinux.org/alpine/v3.22/community' > /etc/apk/repositories
apk add --no-progress ca-certificates cmake ninja clang llvm20 build-base python3 zlib-dev linux-headers
mkdir -p /root/modern-mono
cd /root/modern-mono
wget -q http://10.0.2.2:8766/runtime-v10.0.0.tar.gz -O runtime.tar.gz
printf '%s\n' 'cbc351c6f7afa4fcb622c8faf09f2371933fbd1413672556a410e3bfff061ddf  runtime.tar.gz' | sha256sum -c -
# Extract the native build surface, including CoreCLR headers used by Mono.
tar -xzf runtime.tar.gz \
    runtime-10.0.0/src/mono runtime-10.0.0/src/native \
    runtime-10.0.0/src/coreclr runtime-10.0.0/eng/native \
    runtime-10.0.0/LICENSE.TXT runtime-10.0.0/THIRD-PARTY-NOTICES.TXT
wget -q http://10.0.2.2:8766/build-modern-mono-native.sh -O build.sh
sh build.sh runtime-10.0.0 native-build
