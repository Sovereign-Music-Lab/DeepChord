# From private sources to piano sketches: method and verification

**English** · [한국어](methodology.ko.md)

The current version also includes independently authored public theory/chord foundation RAG. See [foundations and continuing sessions](foundation.md) for distributable assets, repeated requests, and platform scope. PDF preparation below concerns an optional private textbook provider.

This document connects current implementation behavior with the checks a person must perform. See the [README](../README.md) for installation, [training](training.md) for adapters, and [Logic integration](logic.md) for handoff.

## 1. Prepare private PDFs as retrievable evidence

DeepChord does not ship a PDF collector, OCR engine, index builder, or textbook. Prepare a separate private local library and connect it through the interface below. Use material you have rights to use, and keep originals, OCR, score images, excerpts, and indexes outside the public repository.

The following is a recommended external-library workflow, not an automatic DeepChord feature.

1. Record a unique `source_id`, title, PDF SHA-256, and page count for each book. Check the mapping from PDF sequence to printed page numbers. Preserve source identity when different books share page numbers, and do not replace one source with another PDF.
2. Extract existing text and readable page images. Empty native text is a valid observation for an image-only PDF. Store independent OCR with engine, page identity, line coordinates, and text confidence.
3. Inspect the actual image when relying on chord symbols, accidentals, clefs, notes, or rhythm. Text OCR is not OMR; its confidence does not measure note accuracy. Verifying a chord dictionary's index location is different from transcribing the score at that location.
4. Separate raw OCR, reviewed concepts or index locators, editorial applications, and newly composed notes. Attach source ID, pages, image paths, review scope, and limitations to cards. Check ambiguous conventions such as two stacked chords versus a single slash bass, or diminished triads versus diminished sevenths.
5. Index pages and cards, accommodating spacing, chord symbols, and bilingual aliases. BM25 and character n-gram TF-IDF can be combined; embeddings are optional. Preserve book identity and citation IDs when searching multiple sources.
6. Check file coverage, hashes, and page identities. Test predetermined queries for expected concepts, sources, and pages, plus unrelated queries that should return no evidence. Record actual test counts and score-review coverage. A small regression suite is not universal accuracy or complete mastery of a book.

## 2. Connect the library to DeepChord

```sh
export MUSIC_RAG_ROOT=/path/to/private/library
# Check the external provider first:
python "$MUSIC_RAG_ROOT/scripts/rag.py" query 'piano chord inversions' \
  --top 3 --kind concept --context
# Use the same provider through DeepChord:
deepchord rag 'piano chord inversions'
```

Current `core.retrieve` supplements public foundation context by executing `scripts/rag.py` under the configured root with the current Python interpreter and arguments `query TEXT --top 3 --kind concept --context`. Its timeout is 30 seconds and stdout becomes the evidence string. Provider failures propagate rather than silently becoming successful retrieval. Without a configured private library, built-in public foundation retrieval remains active and the run explicitly records that no book evidence was used.

An external provider implementing this interface may search several books internally. DeepChord does not pass `--book` or discover PDFs itself. A `concept` result may include a clearly labeled reviewed index locator as well as a theory card; a locator must not be presented as a note transcription. Stdout should identify source, pages, images, review status, and query-relevant explanation, or explicitly state that no evidence was found. Send provider diagnostics to stderr.

Retrieval scores are not accuracy probabilities. Read the three selected results for relevance and adapt principles to the requested genre, instrumentation, and density. RAG does not change model weights. [LoRA training](training.md) is a separate stage requiring reviewed examples, dataset separation, training, and evaluation.

## 3. Generate symbolic notes locally and validate them

```sh
deepchord compose 'A concise four-bar piano riff in C major, ending on Cmaj7' \
  --bars 4 --model YOUR_INSTALLED_LOCAL_MODEL
```

The Ollama path checks installed-model metadata and refuses cloud models. `--adapter` uses a separate local MLX model and adapter path. The request combines the original prompt with retrieved evidence, labeled as reference data rather than instructions, and requests an original piano sketch without copying book melodies.

The composition command accepts 1-16 bars in 4/4. JSON contains `title`, `tempo`, `bars`, one `chords` label per bar, and `tracks` with note fields `pitch`, `start`, `duration`, and `velocity`. Pitch is sounding MIDI integer C4=60; start and duration use quarter-note beats from zero. The prompt requests piano parts named `Melody` and `Accompaniment`, a memorable motif, dynamics, rests, and connected phrasing. The general validator accepts 1-3 tracks and up to 32 bars; this does not expand the composition command's range.

Validation checks finite numbers, piano pitches 21-108, velocities 1-127, positive durations, form boundaries, and same-pitch overlaps within a track. The default generation prompt uses chord suffixes `maj`, `m`, `maj7`, `maj9`, `m7`, `m9`, `7`, `9`, `13`, and `6`. A limited per-bar comparison checks `Accompaniment` against the chord's pitch-class set and required third and applicable seventh. It does not judge voice leading, playability, or creative quality. A reference book may use chord symbols outside the current supported vocabulary.

Invalid output receives one repair request with the validation error. Failure on both attempts does not become a successful composition. Private runs retain `request.json`, model responses, and `rag-evidence.txt`; successful runs also contain `composition.json`, `validation.json`, `composition.mid`, and `ARRANGEMENT.txt`. Failed runs may lack these final files. See the README for default run locations.

## 4. Performance expression and Logic handoff

The MIDI writer uses PPQ 480, chord markers per bar, and a piano program hint. It releases and reapplies CC64 each bar, ending at zero. This is currently a fixed writer policy, not a detailed model-generated pedal performance. Note lengths, rests, and velocities remain editable in JSON. JSON has no independent controller-event array: preserve the MIDI or Logic project separately after changing pedal events there. Re-exporting JSON regenerates the fixed pedal policy.

`deepchord logic open RUN` creates a new complete MIDI from JSON and asks macOS to open it. It preserves earlier MIDI files and does not discard CC64 through a note-only real-time stream. A person resolves Logic dialogs, chooses a native piano, checks actual register, pedal, and output, and saves the project. A GM program number is an import hint, not a finished sound or verified instrument assignment.

Current MCP integration observes read-only health, session, and region data. Automatic instrument selection, track stacks, plug-in mixing, bounce or stem export, `.logicx` saving, and listening are not completed by this CLI. When doing separate Logic production, re-read project state after user changes and check melody roles, routing, mute/solo states, and unintended MIDI/audio double playback. Verify rendered files and playback paths before claiming aligned stems or a mix. MIDI edits do not automatically update previously rendered audio.

## 5. Evidence required for completion

| Stage | Evidence to check | What it does not establish by itself |
|---|---|---|
| Source preparation | Hashes, page identities, OCR, images, review records | Recognition of every score note and rhythm |
| Retrieval | Relevant sources and pages, no-result handling, regression queries | Model training or composition quality |
| Composition validation | JSON, supported chord checks, MIDI event checks | A pleasing piece or playable fingering |
| Logic open request | Accepted request in `logic-handoff.json` | Completed import into the intended project |
| Actual session verification | Fresh project, regions, controllers, instruments, saved path | A listening assessment |
| Audio and listening | Existing renders, level/stereo checks, separate actual audition | Professional musical quality inferred from metrics |

The CLI leaves `import_verified` and `audio_verified` false even after an accepted open request. If no audio-capable path is available, record that no listening took place. Apply human feedback to editable sources and separate renders; review examples again before using them for training.

## Reproduction checks and publication boundary

```sh
python -m unittest discover -s tests -v
python scripts/check_public.py
python scripts/check_site.py
```

These checks cover implementation boundaries and public files, not full OCR of an external library or musical quality from an actual local model. Commit and push generalized code and documentation only. Keep private PDFs, OCR, score images, cards, retrieved evidence, indexes, training data, models, adapters, generated music, and machine configuration private.
