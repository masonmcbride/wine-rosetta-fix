#!/bin/bash
# SPDX-License-Identifier: LGPL-2.1-or-later
set -euo pipefail
workspace=$(cd -- "$(dirname -- "$0")/../.." && pwd)
if [ -z "${BO2_ENGINE:-}" ] && [ -d "$workspace/bo2-local/engine" ]; then
    BO2_ENGINE="$workspace/bo2-local/engine"
fi
if [ -z "${BO2_PREFIX:-}" ] && [ -d "$workspace/bo2-local/bottle" ]; then
    BO2_PREFIX="$workspace/bo2-local/bottle"
fi
: "${BO2_ENGINE:?Set BO2_ENGINE to your engine directory}"
: "${BO2_PREFIX:?Set BO2_PREFIX to your copied BO2 bottle directory}"
engine=$(cd -- "$BO2_ENGINE" && pwd)
export WINEPREFIX=$(cd -- "$BO2_PREFIX" && pwd)
test -x "$engine/bin/wine64"
test -f "$WINEPREFIX/drive_c/plutonium.exe"
if "$engine/bin/wineserver" -k0 2>/dev/null; then
    echo 'This bottle has an active Wine server. Close its applications before switching engines.' >&2
    exit 1
fi
export WINESERVER="$engine/bin/wineserver" WINELOADER="$engine/bin/wine64"
export DYLD_FALLBACK_LIBRARY_PATH="$engine/lib:/usr/lib"
export WINE_ROSETTA_EXEC_BREAKPOINTS=1
export WINE_ROSETTA_WOW64_BREAKPOINTS=1
export WINE_ROSETTA_CALL_WORKAROUND=1
export WINEDLLOVERRIDES='d3d10core=n,b;d3d11=n,b;d3d12=;dxgi=n,b;winemetal=b'
export WINEMSYNC=1 WINEESYNC=1 WINEFSYNC=0 WINEDEBUG=${WINEDEBUG:--all}
# Suppress MoltenVK's routine device/extension listings; retain errors.
export MVK_CONFIG_LOG_LEVEL=${MVK_CONFIG_LOG_LEVEL:-1}
cd "$WINEPREFIX/drive_c"
if [ "$#" -eq 0 ]; then set -- 'C:\plutonium.exe'; fi
exec "$engine/bin/wine64" "$@"
