# CONTEXT — Sovereign Music Lab website

Updated: 2026-11-10. This site is maintained from the site/ subtree of DeepChord.

## Identity
- Public repository: Sovereign-Music-Lab/Sovereign-Music-Lab.github.io, branch main.
- Public routes: Korean / and English /en/.
- Source of truth: site/ inside the DeepChord checkout. Reconcile remote changes before publishing; do not force-push divergent history.
- Static HTML/CSS/JavaScript; no framework or backend.

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

## Current state and next action
- Bilingual landing page introduces all three projects with first-run steps. On 2026-11-10 fresh macOS ZIP/Git trials found SovaRoll starts empty and SovaFlow synthetic iteration keeps fixed MIDI; copy now explains both and adapter configuration precedence. SovaFlow bundled jobs now honor environment overrides.
- Read both README languages and the paired HTML pages before changing content.
- Keep credits, locale parity, canonical/hreflang, favicon/OG assets and link destinations consistent.
- Product links connect the organization, DeepChord, SovaRoll and SovaFlow; integrations retain their documented limits.
- In DeepChord, run `python3 scripts/check_site.py` and the staged public audit before publishing site/.
- Preview both routes and narrow layouts for UI changes. Verify the Pages build and live URLs after publication.
- This handoff does not authorize future redesigns, model launches or unscheduled publication.

## Navigation
- [Organization](https://github.com/Sovereign-Music-Lab)
- [Website](https://sovereign-music-lab.github.io/)
- [DeepChord](https://github.com/Sovereign-Music-Lab/DeepChord)
- [Sovereign DAW](https://github.com/Sovereign-Music-Lab/sovaroll-DAW)
- [Sovereign Flow](https://github.com/Sovereign-Music-Lab/SovaFlow)

## Update rule
Read AGENTS.md, this file, Git status, then one task. Update this English file after each completed/blocked task and before ending a session. Keep it short; archive detail under docs/context/. Recheck the working directory and remote whenever switching repositories. Git and actual test output outrank stale summaries. Publication must be verified against the remote; this document alone is not proof of a push.
