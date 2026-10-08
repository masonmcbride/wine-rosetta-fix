#!/bin/bash
# SPDX-License-Identifier: LGPL-2.1-or-later
set -euo pipefail
fixture=${1:?Provide a probe fixture name}
shift
case "$fixture" in debug-register-probe|hardware-breakpoint-probe|breakpoint-redirect-probe|single-step-probe|call-ret-step-probe|execution-breakpoint-matrix|internal-call-stack-probe) ;; *) echo 'Unknown fixture' >&2; exit 2 ;; esac
: "${PROBE_ENGINE:?Set PROBE_ENGINE to a compatible Wine engine directory}"
: "${PROBE_PREFIX:?Set PROBE_PREFIX to a dedicated test prefix}"
engine=$(cd -- "$PROBE_ENGINE" && pwd)
root=$(cd -- "$(dirname -- "$0")/.." && pwd)
case "$PROBE_PREFIX" in /*) ;; *) echo 'PROBE_PREFIX must be absolute' >&2; exit 2 ;; esac
export WINEPREFIX="$PROBE_PREFIX" WINESERVER="$engine/bin/wineserver" WINELOADER="$engine/bin/wine64"
export DYLD_FALLBACK_LIBRARY_PATH="$engine/lib:/usr/lib"
export WINEDLLOVERRIDES='mscoree=d;mshtml=d' WINEDEBUG=${WINEDEBUG:--all}
export WINEMSYNC=0 WINEESYNC=0 WINEFSYNC=0
mkdir -p "$root/local/probes"
result=0
for bits in 32 64; do
    case "$bits" in 32) compiler=i686-w64-mingw32-gcc ;; 64) compiler=x86_64-w64-mingw32-gcc ;; esac
    exe="$root/local/probes/$fixture$bits.exe"
    "$compiler" -O2 -o "$exe" "$root/probes/$fixture.c"
    echo "Running $fixture ($bits-bit)"
    "$engine/bin/wine64" "$exe" "$@" || result=1
done
exit "$result"
