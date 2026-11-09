# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Portable MIDI export; native Logic remains a macOS capability."""
import json
from pathlib import Path
from .song_io import validate_song as validate, write_song as write_midi

def export_run(run,out):
    run=Path(run).resolve();out=Path(out).resolve()
    if out.exists():raise FileExistsError(out)
    song=json.loads((run/'composition.json').read_text(encoding='utf-8'));validate(song)
    out.parent.mkdir(parents=True,exist_ok=True);write_midi(song,out)
    return {'midi':str(out),'editable':True,'daw_import_verified':False,'next_step':'Import this Standard MIDI File in your DAW; assign instruments and check playback.'}
