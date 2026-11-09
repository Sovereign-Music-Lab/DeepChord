# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Full-MIDI Logic handoff with separate launch and observation results."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from .mcp import Client
from .core import dump
from .song_io import validate_song as validate, write_song as write_midi


def inspect(config):
    with Client(config) as client:
        return {'server':client.server,'health':client.tool('logic_system','health'),'session':client.tool('logic_project','inspect_session',{'scope':'whole_project','domains':['tracks']})}


def build_project(run, destination, config):
    """Open an owned sketch in an empty Logic session and save a new project.

    The model never chooses commands or paths. Visible region evidence is not
    a note-by-note import or audio verification.
    """
    if sys.platform!='darwin':raise ValueError('Logic Pro requires macOS')
    run=Path(run).expanduser().resolve()
    destination=Path(destination).expanduser().absolute()
    if destination.suffix!='.logicx' or destination.exists() or destination.is_symlink():
        raise ValueError('Choose a new, non-existing .logicx path')
    if not destination.parent.is_dir():raise ValueError('Destination parent must already exist')
    song=json.loads((run/'composition.json').read_text(encoding='utf-8'));validate(song)
    midi=run/f'Logic-Build-{time.time_ns()}.mid';write_midi(song,midi)
    report={'midi':str(midi),'destination':str(destination),'status':'prepared','regions_observed':False,'note_equivalence_verified':False,'audio_verified':False}
    report_path=run/'logic-build.json'
    dump(report_path,report)
    try:
        with Client(config) as client:
            running=client.tool('logic_project','is_running').get('structuredContent',{}).get('message')
            if running not in ('true','false'):raise RuntimeError('Cannot determine whether Logic is running')
            if running=='false':client.tool('logic_project','launch')
            health=client.tool('logic_system','health').get('structuredContent',{})
            if not health.get('logic_pro_running') or not health.get('logic_pro_project_chooser_visible'):
                raise RuntimeError('Logic must show the project chooser; preserve and close any current project first')
            result=subprocess.run(['/usr/bin/open','-b','com.apple.logic10',str(midi)],capture_output=True,text=True,timeout=30)
            if result.returncode:raise RuntimeError('MIDI open request failed: '+result.stderr.strip())
            report['status']='open_requested';dump(report_path,report)
            expected={t['name'] for t in song['tracks']}
            deadline=time.monotonic()+30
            stable_since=None
            while True:
                health=client.tool('logic_system','health').get('structuredContent',{})
                regions=client.tool('logic_project','get_regions').get('structuredContent',{})
                observed=regions.get('regions',[])
                matches=(regions.get('complete') is True and len(observed)==len(expected)
                         and {r.get('name') for r in observed}==expected
                         and all(r.get('kind')=='midi' and r.get('startBar')==1 and r.get('endBar')==song['bars']+1 for r in observed))
                if health.get('logic_pro_running') and health.get('logic_pro_has_window') and not health.get('logic_pro_project_chooser_visible') and matches:
                    if stable_since is None:stable_since=time.monotonic()
                    if time.monotonic()-stable_since>=4:break
                else:stable_since=None
                if time.monotonic()>=deadline:raise RuntimeError('Could not verify the expected MIDI regions; project was not saved automatically')
                time.sleep(1)
            report.update(status='regions_observed',regions_observed=True,regions=observed);dump(report_path,report)
            if destination.exists() or destination.is_symlink():raise RuntimeError('Destination appeared during import; refusing to overwrite')
            saved=client.tool('logic_project','save_as',{'path':str(destination),'confirmed':True}).get('structuredContent',{})
            if not saved.get('verified') or saved.get('observed')!=str(destination) or not destination.is_dir():
                raise RuntimeError('Logic did not verify the requested project path')
            report.update(status='saved',save=saved)
    except BaseException as e:
        report['error']=str(e);dump(report_path,report);raise
    dump(report_path,report)
    return report


def open_run(run,config=None):
    if sys.platform!='darwin':raise ValueError('Logic Pro handoff requires macOS')
    run=Path(run).expanduser().resolve()
    song=json.loads((run/'composition.json').read_text(encoding='utf-8'));validate(song)
    midi=run/'composition.mid'
    # Regenerate from the reviewed event source, retaining all CC64 events.
    # Use a new file so a prior user-edited MIDI is never overwritten.
    handoff=run/f'Logic-Handoff-{time.time_ns()}.mid';write_midi(song,handoff)
    report={'midi':str(handoff),'sha256':hashlib.sha256(handoff.read_bytes()).hexdigest(),'status':'prepared','import_verified':False,'audio_verified':False}
    dump(run/'logic-handoff.json',report)
    # Launch Services opens a standard MIDI file in Logic, retaining tempo/tracks/CCs.
    # This does not close/save/delete any existing project, and no model text is executed.
    result=subprocess.run(['/usr/bin/open','-b','com.apple.logic10',str(handoff)],capture_output=True,text=True,timeout=30)
    report.update(status='open_requested' if result.returncode==0 else 'launch_failed',returncode=result.returncode,error=result.stderr.strip())
    dump(run/'logic-handoff.json',report)
    if result.returncode:raise RuntimeError('Logic launch failed: '+result.stderr)
    if config:
        try:
            with Client(config) as client:
                report['session']=client.tool('logic_project','inspect_session',{'scope':'whole_project','domains':['tracks']})
                report['regions']=client.tool('logic_project','get_regions')
                # Visible AX evidence cannot prove full MIDI content/controller equivalence.
                report['status']='open_requested_with_observation'
        except (OSError,RuntimeError,TimeoutError) as e:report['observation_error']=str(e)
    report['next_step']='If Logic shows a setup/tempo dialog, resolve it; assign suitable instruments and check playback. Request acceptance is not verified import.'
    dump(run/'logic-handoff.json',report)
    return report
