import unittest
import os
from unittest.mock import patch
from tempfile import TemporaryDirectory
from copy import deepcopy
from pathlib import Path
from sovereign_music.arrangement import validate_arrangement, write_arrangement

BASE = {'title':'test','tempo':120,'bars':2,'sections':[{'name':'Intro','start_bar':1}],'tracks':[{'name':'Piano','channel':0,'program':0,'pedal_allowed':True,'notes':[{'pitch':60,'start':0,'duration':1,'velocity':80}],'controllers':[{'beat':0,'control':64,'value':90},{'beat':1,'control':64,'value':0}]},{'name':'Drums','channel':9,'program':0,'notes':[{'pitch':36,'start':0,'duration':0.5,'velocity':90}]}]}

class TestArrangement(unittest.TestCase):
    def test_valid_base(self):
        self.assertTrue(validate_arrangement(BASE)['valid'])

    def test_write_arrangement_format(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.mid"
            write_arrangement(BASE, str(path))

            with open(path, 'rb') as f:
                content = f.read()
                self.assertEqual(content[:14].hex(), '4d546864000000060001000301e0')
                self.assertIn(bytes([0x99, 36, 90]), content)
                self.assertNotIn(bytes([0xc9, 0]), content)

    def test_invalid_arrangements(self):
        with self.subTest(note_pitch_type=True):
            data = deepcopy(BASE)
            data['tracks'][0]['notes'][0]['pitch'] = True
            with self.assertRaises(ValueError):
                validate_arrangement(data)

        with self.subTest(note_start_nan=True):
            data = deepcopy(BASE)
            data['tracks'][0]['notes'][0]['start'] = float('nan')
            with self.assertRaises(ValueError):
                validate_arrangement(data)

        with self.subTest(note_duration_too_small=True):
            data = deepcopy(BASE)
            data['tracks'][0]['notes'][0]['duration'] = 0.000001
            with self.assertRaises(ValueError):
                validate_arrangement(data)

        with self.subTest(piano_pedal_max=True):
            data = deepcopy(BASE)
            data['tracks'][0]['controllers'] = [{'beat':1,'control':64,'value':127}]
            # Assuming pedal logic is checked via controllers or specific pedal flags
            with self.assertRaises(ValueError):
                validate_arrangement(data)

        with self.subTest(start_bar_out_of_bounds=True):
            data = deepcopy(BASE)
            data['sections'][0]['start_bar'] = 2
            with self.assertRaises(ValueError):
                validate_arrangement(data)

        with self.subTest(duplicate_name=True):
            data = deepcopy(BASE)
            data['tracks'][1]['name']='Piano'
            with self.assertRaises(ValueError):
                validate_arrangement(data)

        with self.subTest(duplicate_note_append=True):
            data = deepcopy(BASE)
            data['tracks'][0]['notes'].append({'pitch':60,'start':.5,'duration':.5,'velocity':50})
            with self.assertRaises(ValueError):
                validate_arrangement(data)

    def test_invalid_writer_call(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.mid"
            with self.assertRaises(ValueError):
                write_arrangement({'invalid': 'data'}, str(path))
            self.assertFalse(path.exists())
