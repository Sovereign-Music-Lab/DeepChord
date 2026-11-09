# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
import struct
from pathlib import Path
from sovereign_music.cli import demo
from sovereign_music.midi_preserve import transpose_track_bytes


class MidiPreservationTests(unittest.TestCase):
    def midi(self,events):
        return b'MThd'+struct.pack('>IHHH',6,0,1,480)+b'MTrk'+struct.pack('>I',len(events))+events

    def test_demo_transpose_round_trip_preserves_pedal_and_other_track(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d)/'fixture';demo(run);original=(run/'composition.mid').read_bytes()
            changed,proof=transpose_track_bytes(original,2,2)
            restored,reverse=transpose_track_bytes(changed,2,-2)
            self.assertEqual(restored,original)
            self.assertEqual(proof['pedal_events'],reverse['pedal_events'])
            self.assertGreater(len(proof['pedal_events']),0)
            self.assertEqual(proof['pedal_events'][-1][2],0)
            self.assertEqual(sum(a!=b for a,b in zip(original,changed)),proof['edited_pitch_bytes'])
            self.assertGreater(proof['edited_pitch_bytes'],0)

    def test_rejects_invalid_or_unsafe_transposition(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d)/'fixture';demo(run);original=(run/'composition.mid').read_bytes()
            with self.assertRaises(ValueError):transpose_track_bytes(original,2,25)
            with self.assertRaises(ValueError):transpose_track_bytes(original[:-1],2,1)
            with self.assertRaises(ValueError):transpose_track_bytes(original,0,1)

    def test_running_status_velocity_zero_and_controller_timing(self):
        # Two simultaneous notes, running-status note-ons and velocity-zero offs,
        # with damper on/off between them; no controller bytes may change.
        data=self.midi(bytes.fromhex('00 90 3c 64 00 40 50 00 b0 40 7f 81 70 90 3c 00 00 40 00 00 b0 40 00 00 ff 2f 00'))
        changed,before=transpose_track_bytes(data,0,2)
        restored,after=transpose_track_bytes(changed,0,-2)
        self.assertEqual(restored,data)
        self.assertEqual(before['pedal_events'],[(0,0,127),(240,0,0)])
        self.assertEqual(after['pedal_events'],before['pedal_events'])

    def test_rejects_ambiguous_overlaps_and_pitch_overflow(self):
        overlap=self.midi(bytes.fromhex('00 90 3c 64 00 90 3c 64 00 80 3c 00 00 80 3c 00 00 ff 2f 00'))
        overflow=self.midi(bytes.fromhex('00 90 7f 64 01 80 7f 00 00 ff 2f 00'))
        with self.assertRaises(ValueError):transpose_track_bytes(overlap,0,1)
        with self.assertRaises(ValueError):transpose_track_bytes(overflow,0,1)

if __name__=='__main__':unittest.main()
