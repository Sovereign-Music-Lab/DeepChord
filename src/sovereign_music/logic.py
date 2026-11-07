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
from .core import dump,validate,write_midi


def inspect(config):
    with Client(config) as client:
        return {'server':client.server,'health':client.tool('logic_system','health'),'session':client.tool('logic_project','inspect_session',{'scope':'whole_project','domains':['tracks']})}


def open_run(run,config=None):
    if sys.platform!='darwin':raise ValueError('Logic Pro handoff requires macOS')
    run=Path(run).expanduser().resolve()
    song=json.loads((run/'composition.json').read_text());validate(song)
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
    report['next_step']='If Logic shows a setup/tempo dialog, resolve it; choose a native piano and check playback. Request acceptance is not verified import.'
    dump(run/'logic-handoff.json',report)
    return report
