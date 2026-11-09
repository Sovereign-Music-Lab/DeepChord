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

Install and grant permissions to the MCP server using its upstream instructions. The toolkit reads the selected TOML, negotiates the MCP version, and terminates only its own child process. It does not edit OS permissions or stop another server. If an existing MCP instance owns the MIDI ports, a second instance may report CoreMIDI unavailable; full-file Launch Services handoff still does not depend on those ports.

`deepchord logic build RUN --out /path/to/new.logicx --mcp-config /path/to/logic.toml` launches Logic when needed, requires the project chooser, opens a new MIDI copy, checks region names and bounds, and asks MCP to save a new project. It refuses an existing destination and stops on ambiguous evidence. `session --logic-project /path/to/new.logicx --mcp-config /path/to/logic.toml` performs this after the final successful request. This creates a new project rather than editing an existing one. Saved path and observed regions do not prove note-by-note equivalence or audibility; `logic-build.json` records the status. Saving can fail if the native dialog or project state cannot be verified.

The current upstream `import_file` restricts paths to its own registered temporary files. The toolkit respects that boundary and does not forge temporary paths or rewrite the server. `record_sequence` is not used as a replacement for full MIDI because it does not carry our editable CC64 data.

Sources: [Logic Pro MCP](https://github.com/MongLong0214/logic-pro-mcp), [MCP lifecycle](https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle).

## Public foundations and continuing sessions

[The foundation guide](foundation.md) covers Linux/Windows MIDI export and repeated Mac session handoff. Existing composition JSON records remain supported.

## Editing a note in an existing song

Currently supported: **change one note pitch** or **move one region to another whole bar**. Work takes place in a copy of the saved song; Codex does not need to be running. Verification currently requires the English Logic Event List.

Install the extension once. This needs the Xcode developer tools on a Mac and can take several minutes to fetch and build the source. It leaves existing MCP installations untouched.

```sh
deepchord logic setup --out "$HOME/Music/DeepChord-Logic"
```

The new folder will contain `logic.toml`. If macOS requests Accessibility permission, grant it in System Settings. Setup does not download AI models; prepare Ollama and a local Gemma model separately.

Save the original song first. Replace `song.logicx` with your actual project and choose a new output name. `Piano` is the name of an existing region in this example.

```sh
deepchord logic edit-note "$HOME/Music/song.logicx" 'Raise the first note in Piano by a whole tone' \
  --out "$HOME/Music/song-edited.logicx" --model gemma4:12b-mlx \
  --mcp-config "$HOME/Music/DeepChord-Logic/logic.toml"
```

To move a region, use the command below. Bar 5 is the new start. The length and track stay the same, and notes and pedal events move together.

```sh
deepchord logic move-region "$HOME/Music/song.logicx" 'Move Piano to the start of bar 5' \
  --out "$HOME/Music/song-moved.logicx" --model gemma4:12b-mlx \
  --mcp-config "$HOME/Music/DeepChord-Logic/logic.toml"
```

DeepChord copies the saved source and launches Logic if needed. Gemma identifies the requested region and plans the change. Note edits require unchanged pedal events; region moves require the same shift for every note and pedal event. Other observed MIDI regions are also compared before and after. Success requires saving and reading the saved bytes again. Keep the Mac unlocked and leave Logic untouched while it works. DeepChord brings Logic forward before editing. Long lists can take several minutes because each row is checked in two passes.

Verification currently covers the regions and event lists exposed by Logic. Complex projects with hidden tracks or collapsed stacks are outside the supported scope.

Completion shows the saved project path. The adjacent `song-edited.deepchord` folder retains before/after evidence and a saved verification copy. On failure, inspect the report and working copy. Unverified changes are not saved automatically, and a musical write is never automatically repeated. Unsaved source-session changes, linked files inside a project package, duplicate region names, resizing, splitting, duplication and multi-note edits are currently unsupported. Audio and mix quality are not verified; audition the result separately.

A development project with 122 events (96 notes, 25 pedal events, one program change) passed local-Gemma note selection, native MCP mutation, full event comparison, save, and disk reload on a copy. Source file hashes were unchanged. This does not qualify every Logic version or project. The extension applies to a pinned MIT-licensed Logic Pro MCP revision; its patch and license are included in the package.

A two-region copy also passed Gemma selection and movement of the accompaniment from bar 1 to bar 3. All 12 accompaniment events moved together; all 14 melody events stayed unchanged. Saved-file reload and original-file comparison passed. These tests used Logic Pro 13.0 with its English interface.

Developers can use the [fixture generation and independent check procedure](logic-testing.md) to reproduce these conditions without a private song or private run evidence.
