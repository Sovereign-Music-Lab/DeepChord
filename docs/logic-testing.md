# Reproducing Logic edit checks

**English** · [한국어](logic-testing.ko.md)

This developer procedure uses MIDI made by a public fixture generator instead of a private song. The pattern is neither AI composition nor a music-quality evaluation. Keep generated MIDI, Logic projects and run evidence outside the repository.

## Preparation

Install DeepChord from the repository and complete [Logic extension setup](logic.md#editing-a-note-in-an-existing-song). The model name below must identify a locally installed Gemma. No model download or cloud fallback is performed.

Keep the Mac unlocked and leave Logic and other apps untouched during the trial. Save your own work and close its project first. `logic build` launches Logic if it is closed; when already running, Logic must show its project chooser.

```sh
python scripts/check_logic_fixture.py create "$HOME/Music/DeepChord-fixture"
deepchord logic build "$HOME/Music/DeepChord-fixture" \
  --out "$HOME/Music/DeepChord-fixture/Original.logicx" \
  --mcp-config "$HOME/Music/DeepChord-Logic/logic.toml"
```

`Target` contains 96 notes; `Untouched` contains eight. Each region also contains 25 pedal events and one program change. Both are eight bars long, starting at bar 1. A successful build alone does not prove event equivalence: the independent check below also examines the pre-edit observations.

## Region movement and persistence

```sh
deepchord logic move-region "$HOME/Music/DeepChord-fixture/Original.logicx" \
  'Move Target to the start of bar 3. Keep the other region unchanged.' \
  --out "$HOME/Music/DeepChord-fixture/Moved.logicx" --model gemma4:12b-mlx \
  --mcp-config "$HOME/Music/DeepChord-Logic/logic.toml"
python scripts/check_logic_fixture.py check "$HOME/Music/DeepChord-fixture/Moved.deepchord"
```

The checker independently compares before, after and saved-file reload observations with the generated pattern. It checks note positions, pitches, velocities, lengths and channels; pedal positions, values, channels and counts; program changes; the other region; and original file hashes. It does not reuse the editor's diff functions. Losing even the final pedal release must fail.

To check a backward move, use `Moved.logicx` as input, request “Move Target to the start of bar 1”, and select a new output name. Add `--before-bar 3 --after-bar 1` when checking that result directory.

## Note editing

```sh
deepchord logic edit-note "$HOME/Music/DeepChord-fixture/Original.logicx" \
  'Raise the first note in Target by one semitone. Keep pedal and other notes unchanged.' \
  --out "$HOME/Music/DeepChord-fixture/Pitched.logicx" --model gemma4:12b-mlx \
  --mcp-config "$HOME/Music/DeepChord-Logic/logic.toml"
python scripts/check_logic_fixture.py check "$HOME/Music/DeepChord-fixture/Pitched.deepchord" \
  --after-bar 1 --first-note-semitones 1
```

Always use new output names. Do not repeat a musical write on a failed copy. If a run failed before editing, `check ... --baseline-only` can check just the original imported events. That result does not qualify editing or saving.

## Scope

The checker is specific to this fixed pattern and Logic's 4/4, 960-tick event display. It does not qualify arbitrary songs, hidden tracks, collapsed stacks, instruments or listening quality. It checks test evidence; it does not cryptographically authenticate that evidence. Retain the actual run outcome and original records together.

As of 2026-11-09, the public checker has been compared with the actual multi-region pre-edit observations (122 and 34 events). Full saved-result checking and corruption detection have automated tests using synthetic evidence. **The latest installation's long multi-region move/save/reload live trial remains incomplete.** This page provides a reproduction procedure, not a passing qualification claim. Earlier passing live coverage is distinguished in the [Logic guide](logic.md).
