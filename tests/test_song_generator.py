import unittest
import json
from tempfile import TemporaryDirectory
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import sovereign_music.song_generator as sg

class TestSongGenerator(unittest.TestCase):
    def setUp(self):
            self.PLAN = {
                'title': 'Example',
                'tempo': 100,
                'bars': 24,
                'key': 'C',
                'motif': 'up',
                'sections': [{'name': 'Intro', 'start_bar': 1, 'progression': ['C']}],
                'tracks': [{'name': 'Lead', 'role': 'melody', 'channel': 0, 'program': 0, 'pedal_allowed': False}]
            }

    def test_cache_and_composition(self):
        with TemporaryDirectory() as tmp_dir:
            directory = Path(tmp_dir)
            calls = []
            def fake(*args):
                calls.append(args[2]['start_bar'])
                return {'notes': [{'pitch': 60, 'start': 0, 'duration': 1, 'velocity': 80}], 'summary': 'same'}

            callback = sg.make_block_cache(directory, fake)

            song = sg.compose_arrangement('m', 'p', self.PLAN, block_fn=callback)
            sg.compose_arrangement('m', 'p', self.PLAN, block_fn=callback)

            assert calls == [1, 5, 9, 13, 17, 21]
            assert len(list(directory.glob('*.json'))) == 6
            assert [n['start'] for n in song['tracks'][0]['notes']] == [0, 16, 32, 48, 64, 80]

    def test_repair(self):
        notes = [
            {'pitch': 60, 'start': 0, 'duration': 2, 'velocity': 80},
            {'pitch': 60, 'start': 1, 'duration': 1, 'velocity': 70}
        ]

        corrected, changes = sg.repair_same_pitch_overlaps(notes)

        self.assertEqual(corrected[0]['duration'], 1)
        self.assertEqual(notes[0]['duration'], 2)
        self.assertEqual(changes[0]['old_duration'], 2)
        self.assertEqual(changes[0]['new_duration'], 1)

        for i in range(len(corrected)):
            self.assertEqual(corrected[i]['pitch'], notes[i]['pitch'])
            self.assertEqual(corrected[i]['start'], notes[i]['start'])
            self.assertEqual(corrected[i]['velocity'], notes[i]['velocity'])

        notes = [
            {'pitch': 60, 'start': 0, 'duration': 1, 'velocity': 80},
            {'pitch': 60, 'start': 0, 'duration': 1, 'velocity': 80}
        ]
        with self.assertRaises(ValueError):
            sg.repair_same_pitch_overlaps(notes)

    def test_harmony_review(self):
        original = {'notes': [{'pitch': 61, 'start': 0, 'duration': 1, 'velocity': 80}, {'pitch': 61, 'start': 4, 'duration': 1, 'velocity': 70}], 'summary': 'x'}
        track = {'name': 'Bass', 'role': 'bass', 'channel': 0, 'program': 32}
        progression = ['C', 'C']
        candidate = {'notes': [{'pitch': 60, 'start': 0, 'duration': 1, 'velocity': 80}, {'pitch': 60, 'start': 4, 'duration': 1, 'velocity': 70}]}

        with patch.object(sg, 'call_notes', return_value=('', candidate)):
            result = sg.review_block_harmony('m', original, track, progression)
            self.assertEqual(result['harmony_review']['status'], 'revised')
            self.assertEqual(len(result['harmony_review']['warnings']), 0)
            self.assertEqual(original['notes'][0]['pitch'], 61)
            self.assertEqual(result['notes'][0]['pitch'], 60)

        with patch.object(sg, 'call_notes', return_value=('', {'notes': []})):
            result = sg.review_block_harmony('m', original, track, progression)
            self.assertEqual(result['harmony_review']['status'], 'review_failed')
            self.assertEqual(original['notes'][0]['pitch'], 61)

    def test_continuity_context(self):
        notes = [{'pitch':60+i,'start':i,'duration':1,'velocity':80} for i in range(12)]
        melody = {'notes':notes}
        reference = sg.continuity_context(melody, melody, 12, 4)
        self.assertEqual([n['pitch'] for n in reference['melody_motif']], list(range(60,68)))
        self.assertEqual([n['start'] for n in reference['previous_tail']], list(range(-8,0)))
        self.assertEqual(reference['current_melody'], [])
        reference['previous_tail'][0]['pitch'] = 0
        self.assertEqual(notes[4]['pitch'], 64)

    def test_continuity_and_legacy_resume(self):
        plan = deepcopy(self.PLAN)
        plan['continuity_context_version'] = 1
        plan['tracks'] = [{'name':'Bass','role':'bass','channel':1,'program':32,'pedal_allowed':False}, {'name':'Lead','role':'melody','channel':0,'program':0,'pedal_allowed':False}]
        records = []
        def fake(model,prompt,context,section,track,bars,summary):
            records.append((track['role'],context))
            return {'notes':[{'pitch':60 if track['role']=='melody' else 36,'start':0,'duration':1,'velocity':80}],'summary':'same'}
        song = sg.compose_arrangement('m','p',plan,block_fn=fake)
        self.assertEqual([r[0] for r in records[:2]], ['melody','bass'])
        self.assertEqual([t['name'] for t in song['tracks']], ['Bass','Lead'])
        self.assertEqual(records[1][1]['continuity']['current_melody'][0]['pitch'], 60)
        self.assertEqual(records[0][1]['continuity']['current_melody'], [])
        self.assertEqual(records[2][1]['continuity']['previous_tail'][0]['start'], -16)
        self.assertEqual(records[2][1]['continuity']['melody_motif'][0]['pitch'], 60)
        self.assertEqual(records[2][1]['section_offset_bars'], 4)
        del plan['continuity_context_version']
        records.clear()
        sg.compose_arrangement('m','p',plan,block_fn=fake)
        self.assertEqual(records[0][0], 'bass')
        self.assertNotIn('continuity', records[0][1])

    def test_new_and_existing_plan_versions(self):
        schedule = {'sections':[{'start_bar':1,'arc':'introduce','parts':{'Lead':{'direction':'play','participation':'all'}}}]}
        with TemporaryDirectory() as folder:
            with patch.object(sg.core,'ORG',Path(folder)), patch.object(sg,'make_plan',return_value=deepcopy(self.PLAN)), patch.object(sg,'make_section_schedule',return_value=schedule) as planner:
                run,new_plan = sg.prepare_run('request','model')
                self.assertEqual(new_plan['continuity_context_version'],1)
                self.assertEqual(new_plan['arrangement_context_version'],1)
                self.assertEqual(new_plan['section_schedule'],schedule)
                resumed = sg.prepare_run('request','model',run)[1]
                self.assertEqual(resumed['section_schedule'],schedule)
                self.assertEqual(planner.call_count, 2)
                old_run = Path(folder)/'old'
                old_run.mkdir()
                sg.core.dump(old_run/'request.json',{'prompt':'request','model':'model'})
                sg.core.dump(old_run/'plan.json',deepcopy(self.PLAN))
                self.assertNotIn('arrangement_context_version',sg.prepare_run('request','model',old_run)[1])
                self.assertEqual(planner.call_count, 2)

    def test_current_melody_covers_all_bars(self):
        melody = {'notes':[{'pitch':60,'start':i,'duration':0.5,'velocity':80} for i in range(16)]}
        context = sg.continuity_context({'notes':[]}, melody, 0, 4)
        self.assertEqual([n['start'] for n in context['current_melody']], [0,3,4,7,8,11,12,15])

    def test_planned_participation_and_legacy(self):
        plan=deepcopy(self.PLAN)
        plan['sections']=[{'name':'A','start_bar':1,'progression':['C']},{'name':'B','start_bar':9,'progression':['C']},{'name':'C','start_bar':17,'progression':['C']}]
        plan['tracks']=[{'name':'Lead','role':'melody','channel':0,'program':0,'pedal_allowed':False},{'name':'Bass','role':'bass','channel':1,'program':32,'pedal_allowed':False}]
        plan['arrangement_context_version']=1
        plan['section_schedule']={'sections':[{'start_bar':1,'arc':'opening','parts':{'Lead':{'direction':'theme','participation':'all'},'Bass':{'direction':'rest','participation':'rest'}}},{'start_bar':9,'arc':'development','parts':{'Lead':{'direction':'first','participation':'first'},'Bass':{'direction':'last','participation':'last'}}},{'start_bar':17,'arc':'ending','parts':{'Lead':{'direction':'rest','participation':'rest'},'Bass':{'direction':'resolve','participation':'all'}}}]}
        calls=[]
        def fake(model,prompt,context,section,track,bars,summary):
            calls.append((track['name'],context['start_bar'],context['arrangement']['part_direction']))
            return {'notes':[{'pitch':60 if track['name']=='Lead' else 36,'start':0,'duration':1,'velocity':80}],'summary':'ok'}
        song=sg.compose_arrangement('m','p',plan,block_fn=fake)
        self.assertEqual(calls,[('Lead',1,'theme'),('Lead',5,'theme'),('Lead',9,'first'),('Bass',13,'last'),('Bass',17,'resolve'),('Bass',21,'resolve')])
        self.assertEqual([n['start'] for n in song['tracks'][0]['notes']],[0,16,32])
        self.assertEqual([n['start'] for n in song['tracks'][1]['notes']],[48,64,80])

    def test_rejects_invalid_section_schedule(self):
        plan=deepcopy(self.PLAN)
        valid={'sections':[{'start_bar':1,'arc':'opening','parts':{'Lead':{'direction':'play','participation':'all'}}}]}
        self.assertEqual(sg.validate_section_schedule(plan,valid),valid)
        broken=deepcopy(valid)
        broken['sections'][0]['parts']['Lead']['participation']=[]
        with self.assertRaises(ValueError): sg.validate_section_schedule(plan,broken)
        broken=deepcopy(valid)
        broken['sections'][0]['parts']['Lead']['participation']='rest'
        with self.assertRaises(ValueError): sg.validate_section_schedule(plan,broken)
        broken=deepcopy(valid)
        broken['sections'][0]['parts']['Other']=broken['sections'][0]['parts'].pop('Lead')
        with self.assertRaises(ValueError): sg.validate_section_schedule(plan,broken)
        with self.assertRaises(ValueError): sg.validate_section_schedule(plan,{'sections':None})

    def test_section_schedule_cache_and_corruption(self):
        plan=deepcopy(self.PLAN)
        plan['sections']=[{'name':'A','start_bar':1,'progression':['C']},{'name':'B','start_bar':9,'progression':['C']}]
        plan['tracks']=[{'name':'Lead','role':'melody','channel':0,'program':0,'pedal_allowed':False},{'name':'Bass','role':'bass','channel':1,'program':32,'pedal_allowed':False}]
        calls=[]
        def fake(prompt,model,plan,index,previous,required):
            calls.append((index,list(required)))
            return {'start_bar':plan['sections'][index]['start_bar'],'arc':'section','parts':{'Lead':{'direction':'play','participation':'all'},'Bass':{'direction':'rest' if index==0 else 'play','participation':'rest' if index==0 else 'last'}}}
        with TemporaryDirectory() as folder, patch.object(sg,'make_section_entry',side_effect=fake):
            first=sg.make_section_schedule('p','m',plan,folder)
            second=sg.make_section_schedule('p','m',plan,folder)
            self.assertEqual(first,second)
            self.assertEqual(calls,[(0,[]),(1,['Bass'])])
            paths=list((Path(folder)/'section-plans').glob('*.json'))
            self.assertEqual(len(paths),2)
            for path in paths:
                entry=json.loads(path.read_text())
                if entry['start_bar']==1:
                    del entry['parts']['Bass']
                    path.write_text(json.dumps(entry))
                    break
            with self.assertRaises(ValueError): sg.make_section_schedule('p','m',plan,folder)

    def test_resume_refuses_changed_section_schedule(self):
        schedule={'sections':[{'start_bar':1,'arc':'intro','parts':{'Lead':{'direction':'play','participation':'all'}}}]}
        with TemporaryDirectory() as folder, patch.object(sg.core,'ORG',Path(folder)), patch.object(sg,'make_plan',return_value=deepcopy(self.PLAN)), patch.object(sg,'make_section_schedule',return_value=schedule):
            run,_=sg.prepare_run('request','model')
            changed=deepcopy(schedule)
            changed['sections'][0]['parts']['Lead']['direction']='changed'
            sg.core.dump(run/'section-arrangement.json',changed)
            with self.assertRaisesRegex(ValueError,'saved arrangement differs'):
                sg.prepare_run('request','model',run)
            self.assertEqual(json.loads((run/'section-arrangement.json').read_text()),changed)
