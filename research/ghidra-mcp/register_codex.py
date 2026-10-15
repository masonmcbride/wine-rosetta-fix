#!/usr/bin/env python3
"""Register the verified read-only server, preserving the existing Codex config."""
import datetime
import json
from pathlib import Path
import tomllib

root = Path(__file__).resolve().parent
verification = json.loads((root/'results/verification.json').read_text())
assert verification['mcp_read_only_tools'] == 20
assert verification['mcp_write_rejected'] and verification['http_write_status'] == 404
config = Path('/Users/mason/.codex/config.toml')
original = config.read_text()
parsed = tomllib.loads(original)
name = 'ghidra_wine_readonly'
assert name not in parsed.get('mcp_servers', {}), 'Server already configured; refusing duplicate'
addition = f'''
# Local Wine-only Ghidra MCP; server and Java backend omit mutation operations.
[mcp_servers.{name}]
command = "/Users/mason/w/ghidra/GhidraMCP/.venv/bin/python"
args = [{json.dumps(str(root/'launch_readonly.py'))}]
startup_timeout_sec = 120
tool_timeout_sec = 120
'''
updated = original.rstrip()+'\n'+addition
tomllib.loads(updated)
backup = config.with_name('config.toml.before-ghidra-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
with backup.open('x') as out:
    out.write(original)
assert config.read_text() == original, 'Config changed concurrently; refusing overwrite'
config.write_text(updated)
print('Registered '+name+'; previous configuration: '+str(backup))
