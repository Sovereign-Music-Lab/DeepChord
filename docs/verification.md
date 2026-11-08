# Execution evidence and limitations

**English** · [한국어](verification.ko.md)

Checked on 2026-11-08. Execution checks are distinct from factual and musical quality.

## Public foundations

24 original theory cards, 32 interval formulas, and 384 chords across twelve roots. Checks cover reproducible exports of 408 RAG and 816 training records, formula transpositions, spellings including Cdim7/F#maj7, retrieval, provenance, and overwrite protection. Deduplicating identical targets leaves train 258 / valid 82 / test 92. Transpositions and language variants remain in the same chord-family or theory-card group.

Private textbook PDFs, OCR, prose, page locators, and example scores were not inputs to the public foundation or included in distribution. Public TOML/formulas reproduce exports.

## Actual local composition loop

Two consecutive requests used installed Ollama `gemma4:12b-mlx`. The first passed after one repair; the second received its predecessor and revised accompaniment. Both G7→Cmaj7 labels and melody notes were preserved, with separate JSON, MIDI, explanations, and session records. This two-bar case does not establish reliable compliance with arbitrary revisions.

Separate tests cover continuing after failure, `/quit`, `/new`, resumption, and version preservation. This software task did not modify the open Logic project or audition a new piece.


The same session was resumed for a third request with the local LoRA theory reviewer, followed by Ollama revision. Reviewer output/checks were retained separately and the composition passed JSON/harmony checks.

## Gemma-family LoRA

Text weights from the existing Mac's Gemma 4 12B MLX/Ollama tensors were materialized locally. Global NVFP4-scale compatibility required dequantization with the scale and requantization to affine int4, group 64. This base is **not identical to the original Ollama weights**. Per-tensor relative reconstruction RMSE averaged approximately 0.0972, maximum 0.1228; these are not musical-quality metrics. The original Ollama model was unchanged.

Runs used the official [Gemma 4 12B chat template](https://huggingface.co/google/gemma-4-12B-it/blob/b5deb5d449cec28d5250a5821b0fd42f96ff5110/chat_template.jinja), installed `mlx-lm 0.32.2` / `mlx 0.32.4`, prompt masking, last two layers, rank 8, batch 1, learning rate 0.0001, and seed 42.

| Run | Full held-out test loss | Perplexity |
|---|---|---|
| 20 training steps | 4.715 | 111.647 |
| Separate 200-step run | 3.079 | 21.747 |

Adapter creation, reload, and inference completed. **Factual quality is inadequate.** Four additional queries to the 200-step adapter—Cmaj7, Cdim7, G7, F#m7b5—produced 0/4 fully correct structured answers. Cmaj7/G7 had correct note names but wrong pitch-class integers; other answers also had wrong tones. This small check is not representative accuracy or a creativity benchmark; lower loss does not establish theoretical correctness or better music.

LoRA output remains an unverified proposal. Structured chord answers are checked against formulas, mismatches are recorded, and calculated facts take priority. This adapter is not distributed as a reliable theory model or automatically applied to another Ollama tag. Converted weights, template, adapters, and logs remain local.

## Platforms and DAW

Base-package tests, public audit, and site checks run in a Linux/Windows/macOS CI matrix. Actual Ollama and MLX cases above used Apple Silicon. Optional Transformers/PEFT is implemented for compatible unquantized HF models; PyTorch was absent here, so its real training path was not exercised. GPU, driver, and model qualification is separate.

Native Logic runs on a Mac. File-open requests and MCP observation are distinct from verified import, controllers, instruments, playback, and saving. This version does not automate all Logic editing unattended. Linux/Windows export MIDI for a DAW; instrument sound must be checked there.

Bilingual foundation sections were inspected on desktop and at 390px mobile width. The Korean mobile page had no horizontal overflow.
