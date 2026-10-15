#!/usr/bin/env python3
"""Exercise the real stdio MCP protocol and retain read-only Wine evidence."""
import asyncio
import hashlib
import json
import pathlib
import re
import time
import urllib.error
import urllib.request

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT/'results'
OUT.mkdir(exist_ok=True)
PYTHON = '/Users/mason/w/ghidra/GhidraMCP/.venv/bin/python'
WRITE_NAMES = {'rename_function', 'rename_function_by_address', 'rename_data',
               'rename_variable', 'set_function_prototype', 'set_local_variable_type',
               'set_decompiler_comment', 'set_disassembly_comment'}
ALLOWED = {'get_program_info', 'list_functions', 'list_methods', 'search_functions_by_name',
           'list_classes', 'list_namespaces', 'list_segments', 'list_imports', 'list_exports',
           'list_data_items', 'list_strings', 'get_function_by_address', 'decompile_function',
           'decompile_function_by_address', 'disassemble_function', 'get_xrefs_to',
           'get_xrefs_from', 'get_function_xrefs', 'get_function_calls', 'read_memory'}

def save(name, value):
    data = value.model_dump(mode='json') if hasattr(value, 'model_dump') else value
    (OUT/(name+'.json')).write_text(json.dumps(data, indent=2)+'\n')
    return data

def decoded(result):
    if result.structuredContent is not None:
        return result.structuredContent
    texts = [c.text for c in result.content if c.type == 'text']
    return json.loads(texts[0])

async def main():
    params = StdioServerParameters(command=PYTHON, args=[str(ROOT/'launch_readonly.py')])
    with (OUT/'backend.log').open('w') as log:
        async with stdio_client(params, errlog=log) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                save('initialize', await session.initialize())
                tools = await session.list_tools()
                save('tools', tools)
                names = {t.name for t in tools.tools}
                assert names == ALLOWED, names ^ ALLOWED
                denied = await session.call_tool('rename_function', {})
                save('mcp-write-rejected', denied)
                assert denied.isError
                deadline = time.monotonic()+600
                while True:
                    info = await session.call_tool('get_program_info', {})
                    if not info.isError:
                        break
                    assert time.monotonic() < deadline, info
                    print('Waiting for Wine artifact analysis...', flush=True)
                    await asyncio.sleep(2)
                save('program-info', info)
                print(json.dumps(decoded(info), indent=2), flush=True)
                # Prove the HTTP backend also refuses a mutation route. Empty parameters
                # ensure even a missing hardening gate cannot rename anything.
                log.flush()
                match = re.search(r'Serving .* on (http://127\.0\.0\.1:\d+/)',
                                  (OUT/'backend.log').read_text())
                assert match, 'Backend loopback URL missing from log'
                request = urllib.request.Request(match[1]+'rename_function', data=b'', method='POST')
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                try:
                    opener.open(request, timeout=10)
                    raise AssertionError('Backend unexpectedly accepted POST')
                except urllib.error.HTTPError as error:
                    save('http-write-rejected', {'status': error.code,
                         'body': error.read().decode()})
                    assert error.code == 404
                calls = [
                    ('trap-function', 'get_function_by_address', {'address': '0x38520'}),
                    ('trap-search', 'search_functions_by_name', {'query': 'trap_handler'}),
                    ('predicate-search', 'search_functions_by_name', {'query': 'rosetta_exec_breakpoints'}),
                    ('trap-pseudocode', 'decompile_function_by_address', {'address': '0x38520'}),
                    ('trap-calls', 'get_function_calls', {'address': '0x38520', 'limit': 100}),
                ]
                for name, tool, args in calls:
                    result = await session.call_tool(tool, args)
                    save(name, result)
                    assert not result.isError, result
                offset = 0
                for page in range(20):
                    result = await session.call_tool('disassemble_function',
                        {'address': '0x38520', 'offset': offset, 'limit': 500})
                    save('trap-disassembly-'+str(page), result)
                    assert not result.isError, result
                    data = decoded(result)
                    if not data.get('has_more'):
                        break
                    offset += len(data['items'])
                else:
                    raise AssertionError('Disassembly pagination limit exceeded')
                for addr in ['38b2d', '38b3d', '38b46', '38b4f', '38b60', '38b69', '38b85', '38bdb', '38c31', '38c7c']:
                    result = await session.call_tool('get_xrefs_from', {'address': '0x'+addr})
                    save('flow-'+addr, result)
                    assert not result.isError, result
                print('PASS: 20 read-only MCP tools; MCP and HTTP write rejection; Wine reads captured.', flush=True)
    expected = 'c21bfbe3bcd2aea74a8143a4d69cbb7b59017adc9471e43afd08536487a77591'
    paths = [pathlib.Path('/Users/mason/w/ghidra/artifacts/ntdll.so'),
             ROOT.parents[2]/'bo2-local/engine/lib/wine/x86_64-unix/ntdll.so']
    for path in paths:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    save('verification', {'mcp_read_only_tools': 20, 'mcp_write_rejected': True,
         'http_write_status': 404, 'source_and_snapshot_sha256': expected})

if __name__ == '__main__':
    asyncio.run(main())
