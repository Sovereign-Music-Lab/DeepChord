# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
from sovereign_music.harmony import check, family

def req(segments, comp, melody=None):
    tracks = [{'name': 'Comp', 'notes': comp}] + ([{'name': 'Lead', 'notes': melody}] if melody is not None else [])
    return {'schema': 'deepchord.harmony-request/1', 'title': 't', 'tempo': 80, 'beats_per_bar': 4, 'segments': segments,
            'check_track': 'Comp', 'melody_track': 'Lead', 'tracks': tracks}

def hit(start, dur, pitches): return [{'start': start, 'duration': dur, 'pitch': p} for p in pitches]

class HarmonyTests(unittest.TestCase):
    def test_rootless_ninth_voicings_pass(self):
        segs = [{'bar': 1, 'start': 0, 'beats': 4, 'label': 'Dm9'}, {'bar': 2, 'start': 4, 'beats': 2, 'label': 'Em7b5'}, {'bar': 2, 'start': 6, 'beats': 2, 'label': 'A7'}]
        comp = hit(0, 1.5, [53, 57, 60, 64]) + hit(4, 1.75, [55, 58, 62, 64]) + hit(5.75, 2.25, [55, 61, 64, 66])   # A7 pushed by a 16th: G (b7), C# (3), E (5), F# (13)
        r = check(req(segs, comp))
        self.assertTrue(r['ok'], r); self.assertEqual(r['segments'], 3); self.assertGreater(r['tension_pitch_classes_used'], 0)

    def test_anticipated_hit_counts_for_the_next_chord(self):
        segs = [{'bar': 1, 'start': 0, 'beats': 2, 'label': 'Em7b5'}, {'bar': 1, 'start': 2, 'beats': 2, 'label': 'Eb7'}]
        comp = hit(0, 1.7, [55, 58, 62]) + hit(1.7, 2.3, [55, 61, 65])   # Eb7: G, Db, F(9) starts 0.3 beat early
        self.assertTrue(check(req(segs, comp))['ok'])

    def test_missing_guide_and_outside_tone_are_reported(self):
        segs = [{'bar': 1, 'start': 0, 'beats': 4, 'label': 'Cmaj7'}, {'bar': 2, 'start': 4, 'beats': 4, 'label': 'G7'}]
        comp = hit(0, 4, [60, 67]) + hit(4, 4, [59, 65, 63])           # Cmaj7 without E/B; G7 with Eb (b13 not in the dominant default)
        r = check(req(segs, comp))
        self.assertFalse(r['ok']); self.assertEqual(len(r['guide_tones_missing']), 1); self.assertEqual(len(r['outside_tones']), 1)

    def test_long_melody_note_outside_and_silent_segment(self):
        segs = [{'bar': 1, 'start': 0, 'beats': 4, 'label': 'Am7'}, {'bar': 2, 'start': 4, 'beats': 4, 'label': 'D7'}]
        r = check(req(segs, hit(0, 4, [60, 67]), melody=hit(0, 2, [68]) + hit(2, .5, [70])))
        self.assertEqual(len(r['melody_long_outside']), 1); self.assertEqual(r['silent_segments'], ['bar 2 D7'])

    def test_unsupported_label_and_bad_schema(self):
        r = check(req([{'bar': 1, 'start': 0, 'beats': 4, 'label': 'Cfoo'}], hit(0, 4, [60])))
        self.assertFalse(r['ok']); self.assertEqual(r['unsupported_labels'], ['bar 1: Cfoo'])
        with self.assertRaises(ValueError): check({'schema': 'x'})
        with self.assertRaises(ValueError): check({**req([{'bar': 1, 'start': 0, 'beats': 4, 'label': 'C'}], []), 'check_track': 'Nope'})

    def test_families(self):
        self.assertEqual([family(q) for q in ('7', 'm9', 'maj7', 'm7b5', '7sus4', 'dim7', '9')],
                         ['dominant', 'minor', 'major', 'half-diminished', 'suspended', 'diminished', 'dominant'])

    def test_cli_prints_the_report_for_any_length(self):
        segs = [{'bar': b+1, 'start': b*4, 'beats': 4, 'label': 'Dm9'} for b in range(64)]   # longer than the 32-bar sketch limit
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'h.json'; p.write_text(json.dumps(req(segs, [n for b in range(64) for n in hit(b*4, 2, [53, 57, 60, 64])])), encoding='utf-8')
            out = subprocess.run([sys.executable, '-m', 'sovereign_music', 'harmony', str(p)], capture_output=True, text=True, check=True).stdout
        r = json.loads(out); self.assertTrue(r['ok']); self.assertEqual(r['segments'], 64)

if __name__ == '__main__': unittest.main()
