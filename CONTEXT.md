# CONTEXT — DeepChord

Updated: 2026-11-08 handoff. Baseline before documentation changes: e89e2587b33dfdaf45c87d5d399b7089f2e8fd7e.

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
- Public theory/formula assets, local composition sessions, MIDI/explanations and optional Logic handoff are implemented.
- Current MCP integration is read-only observation; do not describe full automatic Logic production as available.
- The coding-model target does not silently change the composition runtime or its existing default model tag.
- This handoff changes documentation/credits/navigation only, plus explicit public-path allowances for the new Markdown context and skill.
- Website source is site/. Publish only that subtree to Sovereign-Music-Lab.github.io after validating it.
- Keep private books/OCR/RAG, datasets, weights, adapters, runtime settings/logs and personal music private.

## Next action and checks
- Run `git status --short` and read AGENTS.md; no new composition or model launch is authorized by this handoff alone.
- Select one user-requested task before editing runtime code.
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
