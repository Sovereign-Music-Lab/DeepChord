# Logic connection

**English** · [한국어](logic.ko.md)

`logic open RUN` regenerates a new MIDI from `composition.json` and hands it to macOS Launch Services with an argument array (no shell interpolation). It retains notes and per-bar pedal changes. It does not translate the piece into a note-only realtime stream, which would lose the recorded pedal data.

Logic may open a Standard MIDI File as a new project. Studio Grand was automatically assigned in the development GUI test, but the toolkit does not guarantee this on other installations. Watch the native dialog if Logic asks about project creation or tempo. The output report leaves `import_verified` and `audio_verified` false, because the command cannot independently prove note/controller equality or audibility. Do not treat a successful process exit as a finished Logic project.

```sh
deepchord logic open /path/to/run
```

## Optional MCP configuration

Save outside the repository:

```toml
[logic]
command = "/path/to/LogicProMCP"
args = []

[logic.env]
LOGIC_PRO_BUNDLE_ID = "com.apple.logic10"
```

```sh
deepchord logic inspect --mcp-config /path/to/private/logic.toml
deepchord logic open /path/to/run --mcp-config /path/to/private/logic.toml
```

Install and grant permissions to the MCP server using its upstream instructions. The toolkit reads the selected TOML, negotiates the MCP version, calls read-only health/session/region tools, and terminates only its own child process. It does not edit OS permissions or stop another server. If an existing MCP instance owns the MIDI ports, a second instance may report CoreMIDI unavailable; full-file Launch Services handoff still does not depend on those ports.

The current upstream `import_file` restricts paths to its own registered temporary files. The toolkit respects that boundary and does not forge temporary paths or rewrite the server. `record_sequence` is not used as a replacement for full MIDI because it does not carry our editable CC64 data.

Sources: [Logic Pro MCP](https://github.com/MongLong0214/logic-pro-mcp), [MCP lifecycle](https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle).
