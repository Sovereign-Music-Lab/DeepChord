import copy
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from sovereign_music.core import validate, write_midi, harmony_check, local_model
from unittest.mock import patch

SONG={'title':'Test','tempo':76,'bars':1,'chords':['Cmaj7'],'tracks':[{'name':'Piano','notes':[{'pitch':60,'start':0,'duration':1,'velocity':75},{'pitch':60,'start':1,'duration':2,'velocity':65}]}]}

class Checks(unittest.TestCase):
    def test_valid(self): self.assertEqual(validate(SONG)['note_count'],2)
    def test_reject_bad_events(self):
        for key,value in [('pitch',128),('start',-1),('duration',0),('velocity',0),('start',float('nan')),('duration',8)]:
            with self.subTest(key=key,value=value):
                s=copy.deepcopy(SONG); s['tracks'][0]['notes'][0][key]=value
                with self.assertRaises(ValueError): validate(s)
    def test_overlap(self):
        s=copy.deepcopy(SONG); s['tracks'][0]['notes'][1]['start']=0.5
        with self.assertRaises(ValueError): validate(s)
    def test_form(self):
        with self.assertRaises(ValueError): validate(SONG,8)
    def test_cloud_rejected(self):
        with patch('sovereign_music.core.api',return_value={'models':[{'name':'hidden','remote_host':'https://example.com'}]}):
            with self.assertRaises(ValueError):local_model('hidden')
    def test_chord_label_mismatch(self):
        s=copy.deepcopy(SONG);s['tracks'][0]['name']='Accompaniment'
        self.assertTrue(harmony_check(s))
        s['tracks'][0]['notes']=[{'pitch':n,'start':0,'duration':3.8,'velocity':65} for n in [48,52,55,59]]
        self.assertEqual(harmony_check(s),[])
    def test_midi_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.mid'; write_midi(SONG,path); b=path.read_bytes()
        self.assertEqual(b[:4],b'MThd'); self.assertEqual(struct.unpack('>IHHH',b[4:14]),(6,1,2,480))
        pos=14; active=set(); pedal=0; ons=offs=0
        def vlq(data,i):
            value=0
            while True:
                v=data[i]; i+=1; value=(value<<7)|(v&127)
                if v<128:return value,i
        for track in range(2):
            self.assertEqual(b[pos:pos+4],b'MTrk'); size=int.from_bytes(b[pos+4:pos+8],'big'); data=b[pos+8:pos+8+size]; pos+=8+size
            i=t=0
            while i<len(data):
                delta,i=vlq(data,i); t+=delta; status=data[i]; i+=1
                if status==255:
                    kind=data[i]; i+=1; length,i=vlq(data,i); i+=length
                    if kind==47: self.assertEqual(t,1920)
                elif status&240==192:i+=1
                else:
                    key,value=data[i:i+2]; i+=2
                    if status&240==144:
                        self.assertNotIn(key,active); active.add(key); ons+=1
                    elif status&240==128:
                        self.assertIn(key,active); active.remove(key); offs+=1
                    elif status&240==176 and key==64:pedal=value
        self.assertEqual(ons,offs); self.assertEqual(ons,2); self.assertFalse(active); self.assertEqual(pedal,0); self.assertEqual(pos,len(b))

if __name__=='__main__':unittest.main()
