# CONTEXT — DeepChord

Updated: 2026-11-09 local Logic workflow. Version 0.4.0 committed and pushed on 2026-11-09 at the maintainer's explicit instruction ("commit and push everything").

## Identity
- Repository: Sovereign-Music-Lab/DeepChord, branch main.
- Role: compose with a local LLM and work with Logic Pro; preserve editable MIDI and human feedback.
- Runtime: Python 3.11+. Inspect pyproject.toml and README before environment changes.

## Operating policy
- Receiving coding environment: Gemma 4 26B, MLX, M5 Pro, 24 GB unified memory (user-specified target).
- Exact model artifact, quantization, runtime tool support, context cap and performance: not verified by this handoff.
- Use local Gemma 4 for the next coding stage. No silent model substitution or automatic cloud escalation.
- The High/Middle/Low method is reusable planning guidance; it does not override the current model lock or license.
- Read one task and bounded source excerpts. Measure real context/memory usage; do not assume a safe token count from RAM alone.

## Durable decisions
- Credits: Hee-sung Kang, Do-won Lee, Sungmo Park; keep them under README titles.
- README structure: title, authors/credits, abstract, contents, then details; maintain English and Korean editions.
- Tools remain independently usable. Cross-links are navigation, not hidden runtime dependencies.
- Target loop: human → local LLM (optional RAG/LoRA) → Sovereign DAW → autonomous composition → Logic Pro MCP → result → human feedback → repeat.
- Current capability and future architecture are separate. Preserve editable sources and actual evidence.

## Current state
- Source version 0.4.0 on main. Before the push: 74 unit tests, check_public (94 files) and check_site passed locally. Actual composition/edit model `gemma4:12b-mlx`; 26B coding target unverified. Future pushes still need explicit authorization. Workspace `.venv` is editable.
- Native dev `.private/logic-mcp-region-dev`, pinned MIT upstream 9ea55d7c020df4efca1d95c7b4f4a8c3be0c709b. Config `/tmp/deepchord-logic-mcp-region-dev.toml`. System MCP unchanged.
- Full event reader materializes every physical row with consecutive stable values and two complete passes, checks context/count/all filters, restores selection. Raw observations do not prove hidden population or canonical MIDI ownership.
- Single-use preparation binds project/window/physical region/exclusive selection and full baseline. Pitch edits verify semitone steps and exact all-event diff. Whole-bar region moves verify every event's position shift and other fields/bounds. Native never saves. Duplicate observed region names refuse.
- Python copies saved source bytes, asks local Gemma for the target/one operation, snapshots all other observed MIDI regions, edits once, verifies all, saves, reloads a separate saved-byte copy, rechecks all, restores output. Source file hashes checked throughout. Tool failures retain full evidence. No automatic musical retries.
- Pitch E2E PASSED native06, public CLI, installed wheel/release01, including closed-Logic automatic launch. Long fixture: 96 notes,25 pedals,1 program. Small two-region moves PASSED native06, public CLI01 and native10: accompaniment12 events shifted1→3, melody14 unchanged, saved bytes reload/source checks passed.
- Long multi-region source `Multiple-Regions-Original.logicx`: Target122 events, Untouched34. `multiple-region-independent-source-check.json` independently matches every note and pedal to known MIDI source. Private artifacts under `.private/logic-live-test/`; never reuse case paths.
- Long06 failed after menu, full read-only recovery proved both regions unchanged; saved only that verified unchanged copy. Lock was reported later; user unlocked, audio-device alert acknowledged. Lock causality unproven. Long07 failed before musical write (`position_control_changed`); exact owned copy closed saving=no after identity/false-write proof.
- Latest native changes: bind nested physical Tracks owners after closing Event List; read focus last; require real foreground keyboard ownership and no modal; verify playhead/exclusive selection after focus; record menu result and distinct failure reasons. Re-resolve unique bar/beat controls inside the retained window and require numeric continuity before each write because Logic recreates AX controls.
- Latest debug build PASSED 8.11s (`/tmp/deepchord-position-rebind-build.log`). Focused21 tests PASSED (`/tmp/deepchord-position-rebind-tests.log`), including replacement-control continuity/value drift. Earlier selected native91 and Python69 passed. Focused package uses real dev dependency and copied tests with hashes; not the full upstream suite.
- Long08/09 TERMINAL refused before musical/navigation writes.08 observed Finder as actual keyboard owner;09 automatic activation timed out, observations Edge then Codex. No lock assertion: screen was readable. Asked user via async whether Mac can be left on Logic for about5min; answer pending. Current owned unedited copy09 remains open; no live trial active. CUA cycle completed after inspecting08. Do not begin dependent GUI trial until availability answer.
- Bundled patch UPDATED109499bytes SHA2eb6d4a91f1db42ebaf42710b3c85c2e469159710a1ff14da9d06dd10ab61211; clean pinned upstream apply check passed. Includes one foreground activation before baseline, exact PID/no-modal ownership checks thereafter, numeric rebinding and focus guards. Latest debug build72523 terminal. Final focused21 passed (exec20436); installed rc4 Python69 passed (exec62706). rc4 wheel SHA5df8d2432f5674b65f2ad4f95e149a92a21f4d3fb3fbd58c365990ace5740262 installed in `.private/cli-venv-04-rc4`;26-entry content/patch-hash audit passed. Actual Gemma planner checks passed target/move/pitch and unsupported-split/missing-name refusal, without UI (`gemma-rc4-planner-check.json`). Candidate manifest `packaged-candidate-04-rc4.json` retains provenance; live qualification false. Release05 installer exec62777 TERMINAL PASSED476.83s; binary SHAb37e8719bb0bb8a4da102c0acd80e69e257ba714b2b518a6f89f550db54125aa. Installed rc4 client initialized the release server and confirmed required operations (`protocol-check.json`), no UI command. Not live-qualified. No active builds or live tests. Awaiting user foreground availability answer. Older release04/wheels stale; release01 frozen pitch-qualified. No product source edits while build reads checkout. Source and build checkout separate.
- Remaining: long multi-region move/save/reload after user availability; installed CLI backward move and pitch trials, duplicate-name refusal; docs/audits and concise handoff. No general/commercial readiness or listening claims from fixture success.
- Public reproduction tools added: `scripts/check_logic_fixture.py` creates the deterministic long two-region MIDI and independently checks before/after/reloaded notes, pedal/program events and source hashes. `docs/logic-testing.md` and Korean pair document forward/backward moves and pitch trials. Public generator exactly reproduced prior live fixture JSON/MIDI bytes (`.private/repro-fixture-01`). Actual09 baseline matched104notes/50pedals/2programs; this is baseline evidence only, NOT edit/save qualification. Five new corruption/persistence/overwrite tests pass; full Python74 passed (`/tmp/deepchord-fixture-python-tests.log`). These script/docs/test changes do not alter rc4 wheel runtime or release05 native binary.
- Public worktree94/site/whitespace audits passed after reproduction additions. Private data stay ignored. No active build/job/live trial. Foreground availability question remains unanswered: GUI trials must wait. The same availability blocker has persisted for three consecutive goal turns. Goal blocked audit passed: no active build or live-test process, all available offline work completed, latest release live qualification remains false. Resume only after user confirms a foreground test window; do not interpret an automatic goal continuation as that answer. Remaining work requires live UI access; do not manufacture more tests or re-run completed checks as a substitute. Prior detailed context archived `.private/handoff-history/context-before-long08.md`.

## Next action and checks
- Review the 0.4.0 workflows and live-test limitations before claiming general autonomous production. Further existing-project editing requires safe target binding and independent event verification.
- Required checks: `python3 -m unittest discover -s tests -v`, `python3 scripts/check_public.py`, `python3 scripts/check_site.py`.
- Verify current capabilities and checks before making claims. Do not infer music quality from a smoke test.

## Navigation
- [Organization](https://github.com/Sovereign-Music-Lab)
- [Website](https://sovereign-music-lab.github.io/)
- [DeepChord](https://github.com/Sovereign-Music-Lab/DeepChord)
- [Sovereign DAW](https://github.com/Sovereign-Music-Lab/sovaroll-DAW)
- [Sovereign Flow](https://github.com/Sovereign-Music-Lab/SovaFlow)

## Update rule
Read AGENTS.md, this file, Git status, then one task. Update this English file after each completed/blocked task and before ending a session. Keep it short; archive detail under docs/context/. Recheck the working directory and remote whenever switching repositories. Git and actual test output outrank stale summaries. Publication must be verified against the remote; this document alone is not proof of a push.

- 2026-11-10: refreshed the bilingual site introduction for all three tools, including executable SovaFlow and integration limits.

- 2026-11-10: expanded bilingual landing-page beginner instructions for installing and trying each project; clarified DeepChord terminal prerequisites and first output.

- 2026-11-10: tested fresh public ZIP starters and DeepChord install in isolated paths; corrected site guidance for empty SovaRoll, fixed synthetic MIDI and SovaFlow example adapter precedence. Actual gemma4:12b-mlx session failed validation for two requests (harmony, then form boundary); no successful AI output claimed.
