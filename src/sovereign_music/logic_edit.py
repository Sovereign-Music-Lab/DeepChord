# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Bounded local-model editing of the currently open Logic project."""
import json
import hashlib
import math
from pathlib import Path
import re
import shutil
import sys
import time
from . import core
from .mcp import Client

PLAN_SCHEMA={'type':'object','required':['operation','tempo'], 'properties':{
    'operation':{'type':'string','enum':['set_tempo','unsupported']},
    'tempo':{'type':['number','null']}}}


def tempo_plan(request, model):
    """The model proposes a tempo; an explicit BPM in the request bounds it."""
    core.local_model(model)
    response=core.api('/api/chat',{'model':model,'stream':False,'think':False,'format':PLAN_SCHEMA,
        'options':{'num_ctx':4096,'num_predict':256,'temperature':0},
        'messages':[{'role':'system','content':'Interpret the user request. Only an explicit numeric tempo in BPM is supported. Return set_tempo and that number, otherwise unsupported and null. Do not invent a value.'},
                    {'role':'user','content':request}]},timeout=180)
    if response.get('done_reason')=='length':raise ValueError('Model plan was truncated')
    plan=json.loads(response['message']['content'])
    pattern=r'\s*(?:(?:템포(?:를|는)?\s*)|(?:set\s+(?:the\s+)?tempo\s+to\s+))?(\d+(?:\.\d+)?)\s*(?:bpm|비피엠)(?:(?:으로|로)\s*(?:바꿔줘|변경해줘|설정해줘|바꿔|변경|설정))?\s*[.!]?\s*'
    matched=re.fullmatch(pattern,request,re.I)
    value=plan.get('tempo')
    if (plan.get('operation')!='set_tempo' or matched is None or isinstance(value,bool)
        or not isinstance(value,(int,float)) or not math.isfinite(value)
        or value!=float(matched.group(1)) or not 40<=value<=200):
        raise ValueError('Supported request: one explicit tempo from 40 to 200 BPM, e.g. 88 BPM. No changes made.')
    return {'operation':'set_tempo','tempo':value}


def project_identity(client):
    deadline=time.monotonic()+30
    while True:
        info=client.request('resources/read',{'uri':'logic://project/info'})
        contents=info.get('contents',[])
        try:data=json.loads(contents[0]['text'])
        except (IndexError,KeyError,TypeError,ValueError):data={}
        project=data.get('data',{})
        if data.get('identity_source')=='current_document_project_file' and project.get('filePath') and not data.get('unverified'):
            return {'file_path':project['filePath']}
        if time.monotonic()>=deadline:raise RuntimeError('Current Logic project identity is unavailable')
        time.sleep(0.5)


def edit_tempo_copy(source, destination, request, model, config):
    """Save As first, then edit and verify the isolated copy, never the source."""
    if sys.platform!='darwin':raise ValueError('Logic Pro requires macOS')
    source=Path(source).expanduser().resolve(strict=True)
    dest=Path(destination).expanduser().absolute()
    if source.suffix!='.logicx' or not source.is_dir():raise ValueError('Source must be an existing .logicx project')
    if dest.suffix!='.logicx' or dest.exists() or dest.is_symlink() or not dest.parent.is_dir():
        raise ValueError('Destination must be a new .logicx in an existing folder')
    plan=tempo_plan(request,model)
    with Client(config) as client:
        before=project_identity(client)
        if Path(before['file_path']).resolve()!=source:raise RuntimeError('Open the specified source project in Logic first; no edit was made')
        if dest.exists() or dest.is_symlink():raise RuntimeError('Destination already exists')
        saved=client.tool('logic_project','save_as',{'path':str(dest),'confirmed':True}).get('structuredContent',{})
        if not saved.get('verified') or saved.get('observed')!=str(dest) or not dest.is_dir():
            raise RuntimeError('Copy could not be verified; tempo was not changed')
        copy=project_identity(client)
        if Path(copy['file_path']).resolve()!=dest.resolve():raise RuntimeError('Saved copy is not the current project; tempo was not changed')
        # Logic can expose the new document path before its transport controls
        # finish rebuilding. Do not send a write while the window is absent.
        deadline=time.monotonic()+30
        stable_since=None
        while True:
            health=client.tool('logic_system','health').get('structuredContent',{})
            if health.get('logic_pro_running') and health.get('logic_pro_has_window') and not health.get('logic_pro_project_chooser_visible'):
                if stable_since is None:stable_since=time.monotonic()
                if time.monotonic()-stable_since>=5:break
            else:stable_since=None
            if time.monotonic()>=deadline:raise RuntimeError('Logic window did not stabilize; tempo was not changed')
            time.sleep(1)
        if Path(project_identity(client)['file_path']).resolve()!=dest.resolve():raise RuntimeError('Project changed before edit')
        result=client.tool('logic_transport','set_tempo',{'tempo':plan['tempo']}).get('structuredContent',{})
        if not result.get('verified') or result.get('observed')!=plan['tempo']:
            raise RuntimeError('Tempo edit could not be verified; inspect the copy before saving')
        if Path(project_identity(client)['file_path']).resolve()!=dest.resolve():
            raise RuntimeError('Project identity changed after the edit; no automatic save')
        final=client.tool('logic_project','save').get('structuredContent',{})
        if not final.get('verified') or Path(final.get('document_path','')).resolve()!=dest.resolve():
            raise RuntimeError('Final save could not be verified; inspect the copy')
    return {'source':str(source),'copy':str(dest),'model':model,'plan':plan,'tempo_result':result,'save':final,
            'note_edits_supported':False,'audio_verified':False}


class RegionPreparationError(RuntimeError):
    def __init__(self, response):
        self.response = response
        reason = response.get('reason', 'unexpected preparation response')
        super().__init__('Region preparation failed: ' + str(reason) + '; no note edit was requested')


def prepare_region_events(client, project, region):
    """Navigate to an exact observed region; returned raw rows are not edit authority.

    Requires the experimental MCP preparation command. A name alone is never a
    selector: the project, track and region boundaries must also agree.
    """
    project = Path(project).expanduser().resolve(strict=True)
    if project.suffix != '.logicx' or not project.is_dir():
        raise ValueError('Project must be an existing .logicx folder')
    if (region.get('kind') != 'midi' or not isinstance(region.get('name'), str)
        or not region['name'] or any(type(region.get(k)) is not int
                                    for k in ('trackIndex', 'startBar', 'endBar'))
        or region['trackIndex'] < 0 or region['startBar'] < 1
        or region['endBar'] <= region['startBar']):
        raise ValueError('A MIDI region with a track index and explicit bar boundaries is required')
    def check_project():
        if Path(project_identity(client)['file_path']).resolve() != project:
            raise RuntimeError('Current Logic project changed; region preparation stopped')
    check_project()
    response = client.tool('logic_midi', 'prepare_region_events', {
        'project_path': str(project), 'region_name': region['name'],
        'track_index': region['trackIndex'], 'start_bar': region['startBar'],
        'end_bar': region['endBar'],
    }, timeout=330).get('structuredContent', {})
    check_project()
    expected = {'name': region['name'], 'track_index': region['trackIndex'],
                'start_bar': region['startBar'], 'end_bar': region['endBar'], 'kind': 'midi'}
    if (response.get('success') is not True or response.get('selection_verified') is not True
        or response.get('project_path') != str(project)
        or response.get('selected_region_observation') != expected
        or response.get('row_selection_restored') is not True
        or not isinstance(response.get('raw_rows'), list)):
        raise RegionPreparationError(response)
    return response


def pitch_plan(request, snapshot, model):
    """Let the local model choose one existing note from actual observed events.

    This bounded planner does not support region moves, note creation/deletion,
    timing, velocity or multi-note changes. Those need separate verified paths.
    """
    from .logic_events import checked_rows
    rows = checked_rows(snapshot)
    candidates = []
    for index, row in enumerate(rows):
        if row.get('Status', {}).get('value_description') == 'Note':
            pitch = row.get('Num', {}).get('slider_value')
            if isinstance(pitch, bool) or not isinstance(pitch, (int, float)) or not math.isfinite(pitch) or pitch != int(pitch) or not 0 <= pitch <= 127:
                raise ValueError('Observed note pitch is unavailable')
            candidates.append([index, row.get('Position', {}).get('value_description', '').strip(), int(pitch)])
    compact = json.dumps(candidates, ensure_ascii=False, separators=(',', ':'))
    if not candidates or len(compact) > 6000 or not request.strip() or len(request) > 1000:
        raise ValueError('This single-note planner needs a smaller region or a shorter request')
    core.local_model(model)
    schema = {'type':'object', 'required':['operation','row_index','pitch'], 'properties':{
        'operation':{'type':'string','enum':['set_pitch','unsupported']},
        'row_index':{'type':['integer','null']}, 'pitch':{'type':['integer','null']}}}
    response = core.api('/api/chat', {
        'model':model,'stream':False,'think':False,'format':schema,
        'options':{'num_ctx':4096,'num_predict':256,'temperature':0},
        'messages':[
            {'role':'system','content':
             'Plan exactly one existing MIDI note pitch change. Candidate rows are [row_index, bar beat division tick, MIDI_pitch]. '
             'Choose a supplied row index; MIDI pitches are 0..127. All pedal/controllers and other fields must remain unchanged. '
             'If the request requires multiple notes, new/deleted notes, timing, duration, velocity, region edits, or cannot identify one note, '
             'return unsupported with null values. Return only the JSON plan.'},
            {'role':'user','content':request+'\nObserved note candidates: '+compact},
        ],
    }, timeout=180)
    if response.get('done_reason') == 'length':
        raise ValueError('Model edit plan was truncated; no note edit was requested')
    plan = json.loads(response['message']['content'])
    index, pitch = plan.get('row_index'), plan.get('pitch')
    eligible = {row[0]:row[2] for row in candidates}
    if (plan.get('operation') != 'set_pitch' or type(index) is not int or index not in eligible
        or type(pitch) is not int or not 0 <= pitch <= 127 or pitch == eligible[index]):
        raise ValueError('Only one identified existing note pitch change is supported by this planner')
    return {'row_index':index,'expected_pitch':eligible[index],'pitch':pitch}


def package_manifest(project):
    """Hash saved package bytes without following external media links."""
    result = {}
    for path in sorted(project.rglob('*')):
        if path.is_symlink():
            raise ValueError('Linked files inside the Logic package are not supported by copy editing yet')
        if path.is_file():
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            result[str(path.relative_to(project))] = digest.hexdigest()
    if not result:
        raise ValueError('Logic package contains no saved files')
    return result


def choose_region(request, inventory, model):
    """Select from the actual arrangement; never manufacture a region selector."""
    if inventory.get('complete') is not True or not isinstance(inventory.get('regions'), list):
        raise ValueError('The complete region list is unavailable')
    regions = [r for r in inventory['regions'] if r.get('kind') == 'midi']
    compact = json.dumps(regions, ensure_ascii=False, separators=(',', ':'))
    if not regions or len(compact) > 6000:
        raise ValueError('No MIDI regions, or the region list is too large for this planner')
    core.local_model(model)
    response = core.api('/api/chat', {
        'model':model, 'stream':False, 'think':False,
        'format':{'type':'object','required':['region_index'], 'properties':{
            'region_index':{'type':['integer','null']}}},
        'options':{'num_ctx':4096,'num_predict':128,'temperature':0},
        'messages':[
            {'role':'system','content':'Choose exactly one MIDI region identified by the request from the supplied array. Return its zero-based array index. If there is only one region and the user does not name a different region, you may choose it. If the user names a missing region, multiple regions fit, or multiple regions exist without a clear target, return null. Never replace a named but missing region with the only available one. Do not guess.'},
            {'role':'user','content':request+'\nRegions: '+compact},
        ],
    }, timeout=180)
    if response.get('done_reason') == 'length':
        raise ValueError('Region selection was truncated')
    index = json.loads(response['message']['content']).get('region_index')
    if type(index) is not int or not 0 <= index < len(regions):
        raise ValueError('Specify one region by name and, when needed, track and bar')
    return regions[index]


def region_move_plan(request, region, model):
    """Plan only a whole-bar move of the supplied existing region."""
    if type(region.get('startBar')) is not int or type(region.get('endBar')) is not int:
        raise ValueError('Observed region boundaries are required')
    if not request.strip() or len(request) > 1000:
        raise ValueError('A short region move request is required')
    core.local_model(model)
    response = core.api('/api/chat', {
        'model':model,'stream':False,'think':False,
        'format':{'type':'object','required':['operation','start_bar'],'properties':{
            'operation':{'type':'string','enum':['move_region','unsupported']},
            'start_bar':{'type':['integer','null']}}},
        'options':{'num_ctx':4096,'num_predict':128,'temperature':0},
        'messages':[
            {'role':'system','content':'Plan a move of this existing region to the start of one whole bar. Preserve region length, track, notes, pedal and all other events. Return move_region and the requested new start_bar (1..9999). If the request requires resizing, copying, splitting, changing tracks, note edits or any other operation, return unsupported and null. Do not invent a destination.'},
            {'role':'user','content':request+'\nObserved region: '+json.dumps(region,ensure_ascii=False)},
        ],
    }, timeout=180)
    plan = json.loads(response['message']['content']); start = plan.get('start_bar')
    if (response.get('done_reason') == 'length' or plan.get('operation') != 'move_region'
        or type(start) is not int or not 1 <= start <= 9999 or start == region['startBar']
        or not 1 <= region['endBar'] + start - region['startBar'] <= 9999):
        raise ValueError('Only moving one existing region to a different whole bar is supported')
    return {'start_bar':start}


def edit_pitch_copy(source, destination, request, model, config):
    return _edit_copy(source, destination, request, model, config, mode='pitch')


def move_region_copy(source, destination, request, model, config):
    return _edit_copy(source, destination, request, model, config, mode='region_move')


def _edit_copy(source, destination, request, model, config, *, mode):
    """Local model → isolated copy → exact raw diff → save → disk reload.

    All evidence is retained next to the result. Failures preserve the copy and
    never repeat a musical write or save an unverified edit. Only saved source
    bytes are copied; this function never saves the source's unsaved session.
    """
    from .logic_events import verify_pitch_edit, verify_region_shift, checked_rows
    command = {'pitch':'edit_prepared_note_pitch','region_move':'move_prepared_region'}[mode]
    if sys.platform != 'darwin':
        raise ValueError('Logic Pro requires macOS')
    source = Path(source).expanduser().resolve(strict=True)
    destination = Path(destination).expanduser().absolute()
    if source.suffix != '.logicx' or not source.is_dir():
        raise ValueError('Source must be an existing .logicx project folder')
    if (destination.suffix != '.logicx' or destination.exists() or destination.is_symlink()
        or not destination.parent.is_dir() or source in destination.resolve().parents):
        raise ValueError('Choose a new .logicx path outside the source package')
    evidence = destination.with_name(destination.stem + '.deepchord')
    if evidence.exists() or evidence.is_symlink():
        raise ValueError('The result evidence folder already exists; choose a new output name')
    original = package_manifest(source)
    core.local_model(model)
    evidence.mkdir()
    report = {'status':'started','source':str(source),'copy':str(destination),
              'request':request,'model':model,'audio_verified':False,
              'scope':mode+'; raw Event List verification'}
    def checkpoint():
        core.dump(evidence/'report.json', report)
    def progress(message):
        report['phase'] = message
        checkpoint()
        print(message, file=sys.stderr, flush=True)
    def unchanged():
        if package_manifest(source) != original:
            raise RuntimeError('Source files changed during the operation; work stopped')
    checkpoint()
    core.dump(evidence/'source-manifest.json', original)
    try:
        with Client(config) as client:
            # Capability preflight before opening or making the project copy.
            description = json.dumps(client.request('tools/list', {}))
            if 'prepare_region_events' not in description or command not in description:
                raise RuntimeError('Install the DeepChord region-edit MCP extension first')
            progress('Copying the saved project and opening Logic…')
            shutil.copytree(source, destination)
            if package_manifest(destination) != original:
                raise RuntimeError('Project copy does not match the saved source')
            running = client.tool('logic_project','is_running').get('structuredContent',{}).get('message')
            if running == 'false':
                client.tool('logic_project','launch', timeout=330)
            elif running != 'true':
                raise RuntimeError('Logic running state is unavailable')
            client.tool('logic_project','open',{'path':str(destination),'confirmed':True},timeout=330)
            if Path(project_identity(client)['file_path']).resolve() != destination.resolve():
                raise RuntimeError('The requested copy is not the current Logic project')
            inventory = client.tool('logic_project','get_regions').get('structuredContent',{})
            region = choose_region(request, inventory, model)
            report['region'] = region; checkpoint()
            others = [r for r in inventory['regions'] if r.get('kind') == 'midi' and r != region]
            other_before = []
            for index, other in enumerate(others):
                progress(f'Reading other MIDI region {index + 1}/{len(others)}…')
                snapshot = prepare_region_events(client, destination, other)
                checked_rows(snapshot)
                other_before.append(snapshot)
                core.dump(evidence/f'other-{index}-before.json', snapshot)
            if mode == 'region_move':
                plan = region_move_plan(request, region, model)
                report['plan'] = plan; checkpoint()
            progress('Reading every event in the region; leave Logic untouched…')
            before = prepare_region_events(client, destination, region)
            core.dump(evidence/'before.json', before)
            if mode == 'pitch': plan = pitch_plan(request, before, model)
            report['plan'] = plan; checkpoint()
            unchanged()
            progress('Applying Gemma’s change and checking every event…')
            after = client.tool('logic_midi',command, {
                'preparation_id':before['preparation_id'], **plan,
            }, timeout=960).get('structuredContent',{})
            core.dump(evidence/'after.json', after)
            flags = ('raw_pitch_diff_verified','other_raw_events_preserved') if mode == 'pitch' else ('raw_bar_shift_verified','other_raw_fields_preserved','other_observed_region_bounds_preserved')
            if not all(after.get(flag) is True for flag in flags):
                raise RuntimeError('Native edit verification failed: '+str(after.get('reason', 'unknown')))
            def verify_target(snapshot):
                if mode == 'pitch':
                    return verify_pitch_edit(before, snapshot, plan['row_index'], plan['expected_pitch'], plan['pitch'])
                return verify_region_shift(before, snapshot, plan['start_bar'] - region['startBar'])
            def verify_others(project, suffix):
                for index, (other, original_events) in enumerate(zip(others, other_before)):
                    snapshot = prepare_region_events(client, project, other)
                    core.dump(evidence/f'other-{index}-{suffix}.json', snapshot)
                    if checked_rows(snapshot) != checked_rows(original_events) or any(
                        snapshot.get(field) != original_events.get(field) for field in (
                            'selected_region_observation','event_list_region_path','live_header_titles')):
                        raise RuntimeError('Another MIDI region changed; verification stopped')
            report['diff'] = verify_target(after)
            verify_others(destination, 'after')
            unchanged()
            if Path(project_identity(client)['file_path']).resolve() != destination.resolve():
                raise RuntimeError('Project changed before save')
            progress('Saving the verified copy…')
            saved = client.tool('logic_project','save',timeout=330).get('structuredContent',{})
            report['save'] = saved; checkpoint()
            if not saved.get('verified') or Path(saved.get('document_path','')).resolve() != destination.resolve():
                raise RuntimeError('Save could not be verified')
            # A distinct path forces Logic to load the saved bytes, rather than
            # returning the still-open in-memory document as a fake reopen.
            reloaded = evidence/'Saved-verification.logicx'
            saved_manifest = package_manifest(destination)
            shutil.copytree(destination, reloaded)
            if package_manifest(reloaded) != saved_manifest:
                raise RuntimeError('Saved verification copy does not match')
            core.dump(evidence/'saved-manifest.json', saved_manifest)
            progress('Loading the saved file and checking its events again…')
            client.tool('logic_project','open',{'path':str(reloaded),'confirmed':True},timeout=330)
            moved_region = region if mode == 'pitch' else {
                **region,'startBar':plan['start_bar'],
                'endBar':region['endBar'] + plan['start_bar'] - region['startBar'],
            }
            reopened = prepare_region_events(client, reloaded, moved_region)
            core.dump(evidence/'reopened.json', reopened)
            verify_target(reopened)
            verify_others(reloaded, 'reopened')
            unchanged()
            client.tool('logic_project','open',{'path':str(destination),'confirmed':True},timeout=330)
            if Path(project_identity(client)['file_path']).resolve() != destination.resolve():
                raise RuntimeError('Saved result could not be restored as the current project')
            report.update(status='passed',source_files_unchanged=True,saved_events_verified=True,
                          verified_other_midi_regions=len(others))
            report['phase'] = 'Complete'
            checkpoint()
    except BaseException as error:
        report.update(status='failed',error=str(error))
        if isinstance(getattr(error, 'response', None), dict):
            core.dump(evidence/'tool-error.json', error.response)
        try: report['source_files_unchanged'] = package_manifest(source) == original
        except (OSError,ValueError): report['source_files_unchanged'] = False
        checkpoint()
        raise RuntimeError(f'{error}. Evidence: {evidence / "report.json"}. Do not retry a failed musical write on this copy.') from error
    return {**report, 'evidence':str(evidence)}
