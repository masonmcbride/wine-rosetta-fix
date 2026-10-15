#!/usr/bin/env python3
"""Fixed-target stdio MCP launcher. No user-controlled binary/project arguments."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path('/Users/mason/w/ghidra')
REPO = ROOT/'GhidraMCP'
SNAPSHOT = ROOT/'artifacts/ntdll.so'
EXPECTED = 'c21bfbe3bcd2aea74a8143a4d69cbb7b59017adc9471e43afd08536487a77591'

if len(sys.argv) != 1:
    raise SystemExit('This launcher takes no arguments; the analysis target is fixed.')
if hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() != EXPECTED:
    raise SystemExit('Wine artifact checksum mismatch; refusing to analyze another binary.')
manifest = json.loads((ROOT/'readonly-build.json').read_text())
for relative, expected in manifest['protected_files'].items():
    if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() != expected:
        raise SystemExit('Read-only bridge file changed: '+relative)
installation = json.loads((ROOT/'installation.json').read_text())
env = os.environ.copy()
env['JAVA_HOME'] = installation['jdk_home']
env['PATH'] = env['JAVA_HOME']+'/bin:'+env.get('PATH', '')
env['GHIDRA_INSTALL_DIR'] = str(ROOT/'ghidra_12.1.4_PUBLIC')
os.chdir(REPO)
python = REPO/'.venv/bin/python'
args = [str(python), '-m', 'ghidra_mcp', '--headless', '--binary', str(SNAPSHOT),
        '--discard', '--extension-jar', str(REPO/'extension/build/libs/GhidraMCP.jar'),
        '--ready-timeout', '20', '--transport', 'stdio']
os.execve(str(python), args, env)
