# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Editable multitrack MIDI arrangement validation and export."""
from sovereign_music.core import meta, midi_track

def validate_track_types(tracks, form_end):
    def is_int(v): return isinstance(v, int) and not isinstance(v, bool)
    def is_num(v): return isinstance(v, (int, float)) and not isinstance(v, bool)
    def is_valid_range(v, low, high): return is_num(v) and low <= v <= high
    def is_valid_pos(v, limit): return is_num(v) and v > 0 and v <= limit

    if not isinstance(tracks, list) or not (1 <= len(tracks) <= 64):
        raise ValueError("Invalid tracks list length")

    names = set()
    chan_to_prog = {}

    for track in tracks:
        if not isinstance(track, dict): raise ValueError("Track must be dict")

        # Required fields
        for field in ['name', 'channel', 'program', 'notes']:
            if field not in track: raise ValueError(f"Missing {field}")

        name = track['name']
        if not isinstance(name, str) or not name.strip(): raise ValueError("Invalid name")
        if name in names: raise ValueError("Duplicate name")
        names.add(name)

        chan = track['channel']
        prog = track['program']
        if not is_int(chan) or not (0 <= chan <= 15): raise ValueError("Invalid channel")
        if not is_int(prog) or not (0 <= prog <= 127): raise ValueError("Invalid program")

        if chan != 9:
            if chan in chan_to_prog and chan_to_prog[chan] != prog:
                raise ValueError("Channel/Program mismatch")
            chan_to_prog[chan] = prog

        notes = track['notes']
        if not isinstance(notes, list) or not notes: raise ValueError("Invalid notes")
        for n in notes:
            if not isinstance(n, dict): raise ValueError("Note must be dict")
            for f in ['pitch', 'velocity', 'start', 'duration']:
                if f not in n: raise ValueError(f"Missing {f}")

            if not is_int(n['pitch']) or not (0 <= n['pitch'] <= 127): raise ValueError(f"pitch: MIDI integer 0..127, got {n['pitch']}")
            if not is_int(n['velocity']) or not (1 <= n['velocity'] <= 127): raise ValueError(f"velocity: MIDI integer 1..127, got {n['velocity']}")
            if not is_valid_range(n['start'], 0, form_end): raise ValueError(f"start: finite number from 0 through {form_end}, got {n['start']}")
            if not is_valid_pos(n['duration'], form_end): raise ValueError(f"duration: finite positive number at most {form_end}, got {n['duration']}")

        if 'controllers' in track:
            ctrls = track['controllers']
            if not isinstance(ctrls, list): raise ValueError("Controllers must be list")
            for c in ctrls:
                if not isinstance(c, dict): raise ValueError("Controller must be dict")
                for f in ['beat', 'control', 'value']:
                    if f not in c: raise ValueError(f"Missing {f}")
                if not is_valid_range(c['beat'], 0, form_end): raise ValueError("Beat")
                if not is_int(c['control']) or not (0 <= c['control'] <= 127): raise ValueError("Control")
                if not is_int(c['value']) or not (0 <= c['value'] <= 127): raise ValueError("Value")

    return None
def validate_note_intervals(tracks, form_end):
    intervals_by_channel_pitch = {}

    for track in tracks:
        channel = track['channel']
        for note in track['notes']:
            start = note['start']
            duration = note['duration']
            pitch = note['pitch']

            end = start + duration

            if end > form_end:
                raise ValueError(f"Note end exceeds form end. Pitch: {pitch}, Start: {start}, End: {end}, Form End: {form_end}")

            # Rounding to 480 ticks
            start_rounded = round(start * 480)
            end_rounded = round(end * 480)

            if end_rounded <= start_rounded:
                raise ValueError(f"Note duration must be greater than zero. Pitch: {pitch}, Start: {start}, End: {end}")

            key = (channel, pitch)
            if key not in intervals_by_channel_pitch:
                intervals_by_channel_pitch[key] = []

            intervals_by_channel_pitch[key].append((start, end))

    for key in intervals_by_channel_pitch:
        channel, pitch = key
        intervals = sorted(intervals_by_channel_pitch[key])
        max_end_so_far = -float('inf')

        for start, end in intervals:
            if start < max_end_so_far:
                raise ValueError(f"Overlapping notes detected. Channel: {channel}, Pitch: {pitch}, Overlapping Note Start: {start}, Overlapping Note End: {end}, Max End So Far: {max_end_so_far}")
            max_end_so_far = max(max_end_so_far, end)

    return None
def validate_pedals(tracks):
    channel_pedals = {}
    for track in tracks:
        channel = track['channel']
        pedal_allowed = track.get('pedal_allowed', False)

        for ctrl in track.get('controllers', []):
            cc = ctrl['control']
            beat = ctrl['beat']
            value = ctrl['value']

            if cc == 64:
                if pedal_allowed is not True:
                    raise ValueError("Pedal not allowed")

                if channel not in channel_pedals:
                    channel_pedals[channel] = []

                if any(p[0] == beat for p in channel_pedals[channel]):
                    if any(p[1] != value for p in channel_pedals[channel] if p[0] == beat):
                        raise ValueError("Ambiguous pedal event")
                    continue

                channel_pedals[channel].append((beat, value))
            else:
                continue

    for channel, events in channel_pedals.items():
        events.sort()
        last_value = events[-1][1]
        if last_value >= 64:
            raise ValueError("Last pedal value must be < 64")

    return None

def validate_arrangement(song):
    try:
        if not isinstance(song, dict):
            raise TypeError

        title = song.get('title')
        if not isinstance(title, str) or not title.strip():
            raise ValueError

        tempo = song.get('tempo')
        if not isinstance(tempo, (int, float)) or isinstance(tempo, bool) or not (40 <= tempo <= 240):
            raise ValueError

        bars = song.get('bars')
        if not isinstance(bars, int) or isinstance(bars, bool) or not (1 <= bars <= 256):
            raise ValueError

        sections = song.get('sections')
        if not isinstance(sections, list) or len(sections) == 0:
            raise ValueError

        last_bar = 0
        for section in sections:
            if not isinstance(section, dict):
                raise ValueError
            name = section.get('name')
            if not isinstance(name, str) or not name.strip():
                raise ValueError
            start_bar = section.get('start_bar')
            if not isinstance(start_bar, int) or isinstance(start_bar, bool):
                raise ValueError
            if start_bar <= last_bar or start_bar > bars:
                raise ValueError
            if start_bar != 1 and last_bar == 0:
                raise ValueError
            last_bar = start_bar

        if 'tracks' not in song:
            raise KeyError

        tracks = song['tracks']
        if not isinstance(tracks, list):
            raise ValueError

        validate_track_types(tracks, bars * 4)
        validate_note_intervals(tracks, bars * 4)
        validate_pedals(tracks)

        note_count = sum(len(track.get('notes', [])) for track in tracks)

        return {
            'valid': True,
            'bars': bars,
            'tracks': len(tracks),
            'notes': note_count,
            'limitations': ['Not a musical quality assessment']
        }

    except (KeyError, TypeError, ValueError) as e:
        raise ValueError('invalid arrangement') from e

def write_arrangement(song, path):
    """
    Writes a MIDI file based on the provided song structure.
    """
    validate_arrangement(song)
    import struct
    from pathlib import Path
    track_count = len(song['tracks']) + 1
    header = b'MThd' + struct.pack('>IHHH', 6, 1, track_count, 480)
    conductor_events = []
    conductor_events.append((0, 0, meta(3, song['title'])))
    conductor_events.append((0, 0, b'\xff\x51\x03' + round(60000000/song['tempo']).to_bytes(3, 'big')))
    conductor_events.append((0, 0, b'\xff\x58\x04\x04\x02\x18\x08'))
    for section in song['sections']:
        conductor_events.append(((section['start_bar']-1)*1920, 0, meta(6, section['name'])))

    all_chunks = [midi_track(conductor_events, song['bars']*1920)]
    # Re-process instrument tracks
    for track in song['tracks']:
        track_events = []
        track_events.append((0, 0, meta(3, track['name'])))
        if track['channel'] != 9:
            track_events.append((0, 0, bytes([0xC0 | track['channel'], track['program']])))
        for note in track['notes']:
            track_events.append((round(note['start']*480), 3, bytes([0x90 | track['channel'], note['pitch'], note['velocity']])))
            track_events.append((round((note['start'] + note['duration'])*480), 1, bytes([0x80 | track['channel'], note['pitch'], 0])))
        for cc in track.get('controllers', []):
            track_events.append((round(cc['beat']*480), 0, bytes([0xB0 | track['channel'], cc['control'], cc['value']])))
        all_chunks.append(midi_track(track_events, song['bars']*1920))

    Path(path).write_bytes(header + b''.join(all_chunks))
