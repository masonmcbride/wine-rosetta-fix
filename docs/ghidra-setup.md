# Local Ghidra setup

Installed on 2026-10-14 under `/Users/mason/w/ghidra`:

- Official Ghidra 12.1.4 multi-platform release.
- Private Eclipse Temurin JDK 21.0.12.1+1 for macOS ARM64.
- macOS ARM64 native components built with the release's supplied Gradle wrapper
  (`buildNatives`, successful). The official archive does not ship these binaries.

Downloads were checked against the official Ghidra asset SHA-256 and the
Adoptium API's JDK SHA-256. The installation manifest and original downloads are
in `~/w/ghidra/installation.json` and `~/w/ghidra/downloads/`. Java is selected
by the launch wrappers; no system Java registration or shell PATH edit was made.

Launch the GUI from a terminal:

```sh
~/w/ghidra/bin/ghidra
```

Launch headless analysis with:

```sh
~/w/ghidra/bin/ghidra-headless <project-directory> <project-name> <options>
```

The headless usage banner was verified. A further smoke test imported our own
x86_64 DR7 harness as Mach-O, completed auto-analysis, and decompiled its baseline
function successfully using the native ARM64 decompiler. The disposable import
was discarded with `-readOnly`; no harness bytes were changed. See the
[test script](../research/dr7/GhidraInstallSmoke.java) and
[saved log](../research/dr7/results/ghidra-install-smoke.txt), including
`NATIVE_DECOMPILER_SMOKE_PASS 100000560`. This verifies installation functionality,
not the requested Wine-artifact MCP analysis or the GUI.

Ghidra runs locally. A separate MCP bridge can expose selected analysis actions
to the assistant; tool requests go to the bridge, and the bridge invokes or
queries local Ghidra. Returned results enter the chat's model context. Local
analysis does not mean that returned disassembly or pseudocode stays exclusively
on the Mac.

**MCP is now configured and verified.** The Codex server name is
`ghidra_wine_readonly` in `~/.codex/config.toml`. The previous config was backed
up as `~/.codex/config.toml.before-ghidra-20261014-195822`. Registration was
confirmed with the installed extension's `codex mcp get` command. Reload the
VS Code window or start a fresh Codex session if the server is absent from the
tool list; this conversation's pre-existing tool catalog did not hot-reload.

The server uses LaurieWired/GhidraMCP 2.0.0 at commit
`1e980252087b2479a21b9ca6d82d5829538651a7`, installed in
`~/w/ghidra/GhidraMCP`, with locked Python dependencies in its private `.venv`.
A local source patch omits mutation tools in Python and mutation endpoints in
Java unconditionally. Exactly 20 read-only MCP tools were observed; an editing
tool call returned `Unknown tool` and an empty HTTP mutation request returned
404. No script-execution or generic HTTP-dispatch tool is exposed. These checks
do not isolate arbitrary processes running under the user's account.

The [fixed-target launcher](../research/ghidra-mcp/launch_readonly.py) analyzes
`~/w/ghidra/artifacts/ntdll.so`, a read-only copy of our compiled Wine artifact.
It verifies its expected SHA-256 and the audited bridge file hashes before
starting Ghidra. It accepts no target or project arguments. Ghidra imports and
auto-analyzes into a temporary project and discards analysis changes at shutdown;
subsequent API calls cannot rename, annotate, change types or patch bytes.
It does not open or edit a GUI project. Each fresh server process re-analyzes
the artifact, so the first query can take a while or report `NOT_READY`; retry
after analysis completes. Startup and per-tool client timeouts are 120 seconds.

The real MCP verification used
[`verify_mcp.py`](../research/ghidra-mcp/verify_mcp.py), not a simulated backend.
It captured program identity, function metadata, decompilation, all paginated
handler instructions, call references and selected branch edges. Source and
snapshot SHA-256 remained identical after the test. See
[`results/verification.json`](../research/ghidra-mcp/results/verification.json)
and the [optimization study](optimization-study.md) for findings and limitations.

To repeat that test (it overwrites its saved local results):

```sh
~/w/ghidra/GhidraMCP/.venv/bin/python research/ghidra-mcp/verify_mcp.py
```

The launcher can be disabled by setting `enabled = false` in its MCP config
table, or removed with `codex mcp remove ghidra_wine_readonly` when Codex is on
PATH. No background service or login item was installed; the client starts and
stops the stdio server as needed. The interactive GUI launcher remains separate.

Sources: [official release and checksum](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.4_build),
[release-specific Java requirements](https://github.com/NationalSecurityAgency/ghidra/blob/Ghidra_12.1.4_build/README.md),
the installed `GettingStarted.md` section on building native components,
[GhidraMCP upstream](https://github.com/LaurieWired/GhidraMCP), and
[Codex MCP configuration](https://developers.openai.com/codex/mcp).
