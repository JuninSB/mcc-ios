#!/bin/sh
set -eu
umask 077
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
case $(uname -s) in Linux) ;; *) echo 'Installation requires Alpine Linux x86 (iSH).' >&2; exit 69;; esac
command -v apk >/dev/null 2>&1 || { echo 'apk missing. Use Alpine Linux inside iSH.' >&2; exit 69; }
case $(apk --print-arch) in x86) ;; *) echo 'Installation targets Alpine 32-bit x86 only.' >&2; exit 69;; esac
if [ -d /proc/ish ]; then echo 'iSH detected.'; else echo 'Alpine x86 detected; iSH cannot be confirmed.'; fi
for package in mono ca-certificates; do
    if ! apk info -e "$package" >/dev/null 2>&1; then
        [ "$(id -u)" = 0 ] || { echo "Run as root: apk add $package" >&2; exit 77; }
        apk update
        apk search -x "$package" | grep -q . || {
            echo "Package $package unavailable. Enable community for your Alpine release in /etc/apk/repositories, then apk update. Do not mix releases." >&2
            exit 69
        }
        apk add "$package"
    fi
done
command -v mono >/dev/null 2>&1 || { echo 'mono package did not provide a runtime.' >&2; exit 69; }
command -v cert-sync >/dev/null 2>&1 || { echo 'cert-sync missing. Install the full mono package for this Alpine release.' >&2; exit 69; }
if [ "$(id -u)" = 0 ]; then
    cert-sync --quiet /etc/ssl/certs/ca-certificates.crt
else
    cert-sync --user --quiet /etc/ssl/certs/ca-certificates.crt
fi
client_dir="$project_dir/ports/ish/MinecraftClient"
if [ ! -f "$client_dir/bin/Release/MinecraftClient.exe" ] || [ "${MCC_ISH_REBUILD:-0}" = 1 ]; then
    command -v xbuild >/dev/null 2>&1 || { echo 'xbuild missing. Install the full mono package for this Alpine release.' >&2; exit 69; }
    xbuild "$client_dir/MinecraftClient.csproj" /p:Configuration=Release /p:Platform=x86 /verbosity:minimal /nologo
fi
[ -r "$client_dir/bin/Release/MinecraftClient.exe" ] || { echo 'Build did not produce MinecraftClient.exe.' >&2; exit 70; }
echo 'Client built. Launch with sh run.sh.'
