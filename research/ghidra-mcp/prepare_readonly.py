#!/usr/bin/env python3
"""Install our audited, pinned read-only variant; run outside the sandbox.

Does not configure an MCP client. Refuses unexpected upstream source.
"""
import hashlib
import pathlib
import subprocess

ROOT = pathlib.Path('/Users/mason/w/ghidra')
REPO = ROOT/'GhidraMCP'
PIN = '1e980252087b2479a21b9ca6d82d5829538651a7'
assert subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip() == PIN
assert not subprocess.check_output(['git', '-C', str(REPO), 'status', '--porcelain'], text=True), 'Expected clean pinned checkout'

server = REPO/'src/ghidra_mcp/server.py'
text = server.read_text()
marker = '    # ---- Modifications ---------------------------------------------------------------------'
assert text.count(marker) == 1
text = text.replace(marker, '''    # Local research build: mutation tools are never registered.
    # This is unconditional; environment or MCP arguments cannot re-enable them.
    return mcp

'''+marker)
text = text.replace('Prefer the address-based tools for modifications,\nsince function names can be ambiguous.',
                    'This local build exposes read-only analysis tools. Decompiler pseudocode is not authoritative semantics.')
server.write_text(text)

java = REPO/'extension/src/main/java/com/lauriewired/ghidramcp/http/BackendHttpServer.java'
text = java.read_text()
old = '\t\troutes.put(path, new Route("POST", true, handler));'
assert text.count(old) == 1
text = text.replace(old, '\t\t// Local research build: do not register mutation routes, even for direct HTTP clients.')
java.write_text(text)

source = pathlib.Path('/Users/mason/w/cs/fun/wine-rosetta-debugregs/bo2-local/engine/lib/wine/x86_64-unix/ntdll.so')
expected = 'c21bfbe3bcd2aea74a8143a4d69cbb7b59017adc9471e43afd08536487a77591'
contents = source.read_bytes()
assert hashlib.sha256(contents).hexdigest() == expected
artifacts = ROOT/'artifacts'
artifacts.mkdir(exist_ok=True)
snapshot = artifacts/'ntdll.so'
assert not snapshot.exists(), 'Refusing to overwrite artifact snapshot'
snapshot.write_bytes(contents)
snapshot.chmod(0o444)

patch = subprocess.check_output(['git', '-C', str(REPO), 'diff', '--', 'src/ghidra_mcp/server.py',
                                'extension/src/main/java/com/lauriewired/ghidramcp/http/BackendHttpServer.java'], text=True)
(ROOT/'readonly-hardening.patch').write_text(patch)
print('Pinned source hardened; artifact snapshot copied and hash verified.')
