# DeepChord — Sovereign Music Lab

Keep original PDFs and book-derived OCR, RAG indexes/excerpts, model weights, adapters, private datasets, generated music, machine configuration and runtime logs private. The user-authorized public foundation is independently authored general theory and algorithmic chord formulas in src/sovereign_music/assets/foundation.toml, plus reproducible export/training code; do not copy private book cards, page locators, prose, scores, or book structure into it. Do not stage or publish them. Runtime defaults to an external user data directory; local experiments belong in .private/ (ignored). No remote publication without the user's request.

Use the configured local model only. Never substitute a cloud model silently. Report DAW request acceptance, MIDI import verification, audible instruments and listening quality as separate states. Do not claim training quality from a smoke test. Run tests and scripts/check_public.py before committing. Build distributions only from src/, without private assets.

Public site routes are Korean `/` and English `/en/`. Keep both pages, metadata, interactive messages and paired README/docs translations in sync. Credit the user as Sungmo Park. Project code uses Apache-2.0; retain LICENSE and NOTICE. Brand-image audit exceptions are exact reviewed paths and hashes, never a general binary allowance. Run scripts/check_site.py for website, translation or license updates.


## Compact English handoff

Read CONTEXT.md after this file and before the task. Update it after each completed/blocked task and before ending the session; archive detail under docs/context/. The next coding handoff targets local Gemma 4 26B / MLX on M5 Pro 24 GB, with exact runtime/model/context capacity still to be measured. This does not change the composition model configuration automatically. The shared model-tier skill describes a reusable strategy; the current local-only policy remains authoritative. Keep authors/credits, abstract, contents and project navigation near the top of both README editions.
