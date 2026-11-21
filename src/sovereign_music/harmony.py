# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Chord-segment harmony check for a whole song of any length (no model, no bar limit).

`deepchord harmony REQUEST.json` reads a deepchord.harmony-request/1:
  {"schema": "deepchord.harmony-request/1", "title": str, "tempo": number, "beats_per_bar": 4,
   "segments": [{"bar": 1, "start": 0.0, "beats": 4.0, "label": "Dm9"}, ...],      # start in beats from the song start
   "check_track": "Rhodes_Comp", "melody_track": "Lead" (optional),
   "tracks": [{"name": str, "notes": [{"start": beats, "duration": beats, "pitch": 0-127}, ...]}, ...]}
and reports, per chord segment, whether the harmony track states the chord (its 3rd and 7th, or 3rd/4th on chords without a 7th)
and which of its pitch classes are neither chord tones nor the usual available tensions of that chord family.
A note belongs to the segment it overlaps most, so a comping hit anticipated by a swung 16th counts for the chord it pushes into.
This is a label-consistency check, not a judgment of musical quality."""
from .foundation import chord

SCHEMA = 'deepchord.harmony-request/1'
# Available tensions (semitones above the root) per chord family, beyond the chord's own tones.
TENSIONS = {
    'dominant': {2, 9},          # 9, 13
    'minor': {2, 5, 9},          # 9, 11, 13 (Dorian)
    'major': {2, 6, 9},          # 9, #11, 13
    'half-diminished': {2, 5, 8},  # 9 (Locrian #2), 11, b13
    'diminished': {2, 5, 8, 11},
    'suspended': {2, 9},
    'other': set(),
}

def family(quality):
    if quality in ('m7b5',): return 'half-diminished'
    if quality.startswith('dim'): return 'diminished'
    if 'sus' in quality: return 'suspended'
    if quality.startswith('m') and not quality.startswith('maj'): return 'minor'
    if quality.startswith('maj') or quality in ('maj', '6', '6/9', 'add9'): return 'major'
    if quality[:1].isdigit(): return 'dominant'
    return 'other'

def _guides(fact):
    want = [i for d, i in zip(fact['degrees'], fact['intervals']) if d in (3, 7)]
    if not any(d == 3 for d in fact['degrees']):   # sus chords: the 4th/2nd stands in for the 3rd
        want += [i for d, i in zip(fact['degrees'], fact['intervals']) if d in (2, 4)]
    return {(fact['root_pc'] + i) % 12 for i in want}

def _segment_of(note, segs):
    s, e = note['start'], note['start'] + max(note.get('duration', 0.0), 1e-6)
    best, ov = None, 0.0
    for k, g in enumerate(segs):
        o = min(e, g['start'] + g['beats']) - max(s, g['start'])
        if o > ov + 1e-9: best, ov = k, o
    return best

def check(req):
    if req.get('schema') != SCHEMA: raise ValueError(f'harmony request schema must be {SCHEMA}')
    segs = sorted(req['segments'], key=lambda g: g['start'])
    if not segs: raise ValueError('harmony request has no segments')
    tracks = {t['name']: t['notes'] for t in req['tracks']}
    comp_name = req.get('check_track')
    if comp_name not in tracks: raise ValueError(f'check_track {comp_name!r} is not among the tracks {sorted(tracks)}')
    mel_name = req.get('melody_track')
    facts, unsupported = [], []
    for g in segs:
        try: facts.append(chord(g['label']))
        except ValueError: facts.append(None); unsupported.append(f"bar {g['bar']}: {g['label']}")
    comp_pcs = [set() for _ in segs]
    for n in tracks[comp_name]:
        k = _segment_of(n, segs)
        if k is not None: comp_pcs[k].add(n['pitch'] % 12)
    missing, outside, tension_use, silent = [], [], 0, []
    for g, fact, pcs in zip(segs, facts, comp_pcs):
        if fact is None: continue
        if not pcs: silent.append(f"bar {g['bar']} {g['label']}"); continue
        root = fact['root_pc']; tones = set(fact['pitch_classes'])
        tens = {(root + i) % 12 for i in TENSIONS[family(fact['quality'])]}
        lost = _guides(fact) - pcs
        if lost: missing.append(f"bar {g['bar']} {g['label']}: missing {sorted(lost)} in {sorted(pcs)}")
        out = pcs - tones - tens
        if out: outside.append(f"bar {g['bar']} {g['label']}: outside {sorted(out)} in {sorted(pcs)}")
        tension_use += len(pcs & (tens - tones))
    mel_out = []
    if mel_name in tracks:
        for n in tracks[mel_name]:
            if n.get('duration', 0) < 1.0: continue
            k = _segment_of(n, segs)
            if k is None or facts[k] is None: continue
            fact = facts[k]; root = fact['root_pc']
            ok = set(fact['pitch_classes']) | {(root + i) % 12 for i in TENSIONS[family(fact['quality'])]}
            if n['pitch'] % 12 not in ok: mel_out.append(f"bar {segs[k]['bar']} {segs[k]['label']}: melody pitch {n['pitch']} ({n['duration']} beats)")
    return {'schema': 'deepchord.harmony-report/1', 'title': req.get('title'), 'segments': len(segs), 'check_track': comp_name,
            'unsupported_labels': unsupported, 'guide_tones_missing': missing, 'outside_tones': outside, 'silent_segments': silent,
            'tension_pitch_classes_used': tension_use, 'melody_track': mel_name if mel_name in tracks else None, 'melody_long_outside': mel_out,
            'ok': not (unsupported or missing or outside),
            'note': 'Label-consistency check of chord tones and available tensions; it does not judge musical quality and nobody listened.'}
