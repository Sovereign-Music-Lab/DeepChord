# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Dispatch between piano sketches and editable multitrack arrangements."""
from . import core, arrangement

def validate_song(song):
    if 'sections' in song:
        return arrangement.validate_arrangement(song)
    else:
        return core.validate(song)

def write_song(song, path):
    if 'sections' in song:
        arrangement.write_arrangement(song, path)
    else:
        core.write_midi(song, path)
