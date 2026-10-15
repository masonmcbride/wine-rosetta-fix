#!/usr/bin/env python3
"""Record checksums of the audited read-only files after compiling."""
import hashlib
import json
from pathlib import Path

root = Path('/Users/mason/w/ghidra')
names = ['GhidraMCP/src/ghidra_mcp/server.py', 'GhidraMCP/src/ghidra_mcp/backend.py',
         'GhidraMCP/src/ghidra_mcp/headless.py', 'GhidraMCP/src/ghidra_mcp/cli.py',
         'GhidraMCP/extension/build/libs/GhidraMCP.jar']
manifest = {'upstream_commit': '1e980252087b2479a21b9ca6d82d5829538651a7',
            'protected_files': {name: hashlib.sha256((root/name).read_bytes()).hexdigest()
                                for name in names}}
(root/'readonly-build.json').write_text(json.dumps(manifest, indent=2)+'\n')
