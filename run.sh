#!/bin/sh
set -eu
umask 077
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
client="$project_dir/ports/ish/MinecraftClient/bin/Release/MinecraftClient.exe"
if ! command -v mono >/dev/null 2>&1 || [ ! -f "$client" ]; then
    sh "$project_dir/install.sh"
fi
command -v mono >/dev/null 2>&1 || { echo 'Mono missing. Run sh install.sh.' >&2; exit 69; }
[ -r "$client" ] || { echo 'Client build missing. Run sh install.sh.' >&2; exit 66; }
if [ -n "${MCC_ISH_HOME:-}" ]; then
    state_dir=$MCC_ISH_HOME
elif [ -n "${XDG_CONFIG_HOME:-}" ]; then
    state_dir=$XDG_CONFIG_HOME/mcc-ish
else
    user_home=${HOME:-}
    if [ -z "$user_home" ]; then
        user_home=$(awk -F: -v user_id="$(id -u)" '$3 == user_id { print $6; exit }' /etc/passwd)
    fi
    [ -n "$user_home" ] || { echo 'Home directory unavailable. Set MCC_ISH_HOME to a private configuration directory.' >&2; exit 78; }
    state_dir=$user_home/.config/mcc-ish
fi
mkdir -p "$state_dir"
chmod 700 "$state_dir"
cd "$state_dir"
exec mono "$client" "$@" BasicIO-NoColor
