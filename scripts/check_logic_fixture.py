#!/usr/bin/env python3
# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Generate an original test fixture and independently check live Logic evidence.

No GUI commands or model calls. The verifier uses known 4/4, 960-tick Logic
positions, not the editor's own diff functions. This is not a general MIDI parser.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def fixture():
    return {
        'title': 'Independent multi-region regression fixture',
        'tempo': 96, 'bars': 8, 'chords': ['Cmaj7'] * 8,
        'tracks': [
            {'name': 'Untouched', 'notes': [
                {'pitch': 48 + i % 3, 'start': i * 4, 'duration': 2, 'velocity': 50 + i}
                for i in range(8)]},
            {'name': 'Target', 'notes': [
                {'pitch': 60 + i % 7, 'start': i / 3, 'duration': .25, 'velocity': 65 + i % 12}
                for i in range(96)]},
        ],
    }


def require(condition, message):
    if not condition:
        raise ValueError(message)


def create(directory):
    from sovereign_music.core import write_midi
    directory = Path(directory).expanduser()
    directory.mkdir()  # Existing files and folders must never be overwritten.
    song = fixture()
    (directory / 'composition.json').write_text(json.dumps(song, indent=2) + '\n')
    write_midi(song, directory / 'composition.mid')
    return {'fixture': str(directory.resolve()), 'ai_composition': False,
            'target_notes': 96, 'untouched_notes': 8, 'pedals_per_region': 25}


def position(text, *, duration=False):
    words = text.split()
    require(len(words) == 4, 'Expected a four-part Logic event position')
    a, b, c, d = map(int, words)
    origin = 0 if duration else 1
    require(all(x >= origin for x in (a, b, c, d)), 'Invalid event position')
    return (a-origin)*3840 + (b-origin)*960 + (c-origin)*240 + d-origin


def check_snapshot(snapshot, name, *, start_bar=1, first_note_semitones=0):
    channel = {'Untouched': 1, 'Target': 2}[name]
    require(start_bar >= 1, 'Invalid expected start bar')
    expected_region = {'name': name, 'kind': 'midi', 'track_index': channel-1,
                       'start_bar': start_bar, 'end_bar': start_bar+8}
    require(snapshot.get('selected_region_observation') == expected_region, 'Wrong region or bounds')
    require(snapshot.get('event_list_region_path') == name, 'Wrong Event List region')
    require(snapshot.get('row_selection_restored') is True, 'Selection restoration unverified')
    require(snapshot.get('observed_rows_content_stable') is True, 'Unstable event rows')
    for key in ('noteEvents', 'controller', 'programChange', 'pitchBend',
                'aftertouch', 'polyAftertouch', 'systemExclusive'):
        require(snapshot.get('event_list_filter_states', {}).get(key) is True, 'An event filter is hidden')
    rows = snapshot['raw_rows']
    require(snapshot.get('event_list_item_count_text') == f'{len(rows)} Events', 'Event count mismatch')
    notes, controllers, programs = Counter(), Counter(), Counter()
    for row in rows:
        at = position(row['Position']['value_description'])
        status = row['Status']['value_description']
        ch = row['Ch']['slider_value']
        val = int(row['Val']['value_description'])
        if status == 'Note':
            notes[at, row['Num']['slider_value'], val,
                  position(row['Length/Info']['value_description'], duration=True), ch] += 1
        elif status == 'Control':
            controllers[at, row['Num']['slider_value'], val, ch] += 1
        elif status == 'Program':
            programs[at, val, ch] += 1
        else:
            raise ValueError('Unexpected event type in the known fixture: ' + status)
    shift = (start_bar-1)*3840
    # This fixture's starts and durations land exactly on integral Logic ticks.
    if name == 'Target':
        expected_notes = Counter((i*320+shift, 60+i%7+(first_note_semitones if i == 0 else 0),
                                  65+i%12, 240, channel) for i in range(96))
    else:
        require(first_note_semitones == 0, 'Untouched must not be edited')
        expected_notes = Counter((i*3840+shift, 48+i%3, 50+i, 1920, channel) for i in range(8))
    expected_pedals = Counter(
        [(i*3840+shift, 64, 0, channel) for i in range(8)] +
        [(i*3840+60+shift, 64, 90, channel) for i in range(8)] +
        [((i+1)*3840-50+shift, 64, 0, channel) for i in range(8)] +
        [(8*3840+shift, 64, 0, channel)])
    require(notes == expected_notes, name + ': note time/pitch/velocity/length/channel mismatch')
    require(controllers == expected_pedals, name + ': pedal time/value/channel/count mismatch')
    require(programs == Counter({(shift, 0, channel): 1}), name + ': program change mismatch')
    return {'notes': sum(notes.values()), 'pedals': sum(controllers.values()), 'programs': sum(programs.values())}


def saved_files(project):
    require(project.is_dir() and project.suffix == '.logicx', 'Source is not a Logic project folder')
    result = {}
    for path in sorted(project.rglob('*')):
        require(not path.is_symlink(), 'Linked project files are outside this fixture check')
        if path.is_file():
            with path.open('rb') as stream:
                result[str(path.relative_to(project))] = hashlib.file_digest(stream, 'sha256').hexdigest()
    require(bool(result), 'Empty source project')
    return result


def check(directory, *, before_bar=1, after_bar=3, first_note_semitones=0, baseline_only=False):
    directory = Path(directory).expanduser()
    def read(name):
        return json.loads((directory / name).read_text())
    report = read('report.json')
    results = {}
    phases = [('before', before_bar, 0)]
    if not baseline_only:
        require(report.get('status') == 'passed' and report.get('saved_events_verified') is True,
                'The live edit/save/reload did not pass')
        require((before_bar != after_bar) != (first_note_semitones != 0),
                'Check one region move or one pitch edit at a time')
        phases += [('after', after_bar, first_note_semitones), ('reopened', after_bar, first_note_semitones)]
    for suffix, bar, semitones in phases:
        results['Target-'+suffix] = check_snapshot(read(suffix+'.json'), 'Target',
                                                   start_bar=bar, first_note_semitones=semitones)
        results['Untouched-'+suffix] = check_snapshot(read('other-0-'+suffix+'.json'), 'Untouched')
    require(saved_files(Path(report['source'])) == read('source-manifest.json'), 'Original saved files changed')
    return {'status': 'passed', 'scope': 'baseline_only' if baseline_only else 'saved_fixture_events',
            'source_files_unchanged': True, 'checks': results, 'audio_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    make = commands.add_parser('create'); make.add_argument('directory')
    verify = commands.add_parser('check'); verify.add_argument('directory')
    verify.add_argument('--before-bar', type=int, default=1)
    verify.add_argument('--after-bar', type=int, default=3)
    verify.add_argument('--first-note-semitones', type=int, default=0)
    verify.add_argument('--baseline-only', action='store_true', help='Only check pre-edit events; does not qualify editing')
    args = parser.parse_args()
    try:
        result = create(args.directory) if args.command == 'create' else check(
            args.directory, before_bar=args.before_bar, after_bar=args.after_bar,
            first_note_semitones=args.first_note_semitones, baseline_only=args.baseline_only)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f'Fixture check failed: {error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
