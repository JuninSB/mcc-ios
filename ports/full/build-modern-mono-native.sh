#!/bin/sh
# Native feasibility experiment only. This does not build the managed libraries
# and is not a usable .NET distribution or an MCC release.
set -eu
if [ "$#" -ne 2 ]; then
    echo 'Usage: sh build-modern-mono-native.sh RUNTIME_SOURCE OUTPUT_DIRECTORY' >&2
    exit 2
fi
source_dir=$(cd "$1" && pwd)
mkdir -p "$2"
output_dir=$(cd "$2" && pwd)
test -f "$source_dir/src/mono/CMakeLists.txt"
test "$(uname -s)" = Linux
case "$(uname -m)" in i386|i486|i586|i686) ;; *) echo 'This experiment requires Linux x86 (32-bit).' >&2; exit 2 ;; esac

cmake -S "$source_dir/src/mono" -B "$output_dir" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
    -DCLR_CMAKE_HOST_ARCH=x86 -DCLR_CMAKE_TARGET_ARCH=x86 \
    -DCLR_CMAKE_HOST_OS=linux -DCLR_CMAKE_TARGET_OS=linux \
    -DCLR_CMAKE_TARGET_UNIX=1 \
    -DCLR_CMAKE_HOST_LINUX_MUSL=1 -DCLR_CMAKE_TARGET_LINUX_MUSL=1 \
    -DCLR_CMAKE_USE_SYSTEM_ZLIB=1 \
    -DENABLE_LLVM_RUNTIME=OFF
echo MCC_MODERN_MONO_CONFIGURE_PASS
cmake --build "$output_dir" --parallel "${MCC_BUILD_JOBS:-2}"
echo MCC_MODERN_MONO_NATIVE_BUILD_PASS
