# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Experimental long-form generation using a local model."""
import json
from . import core
from .foundation import chord
from .arrangement import validate_arrangement, validate_track_types, validate_note_intervals, write_arrangement

def make_plan(prompt, model):
    core.local_model(model)

    system_prompt = (
        "Create an ORIGINAL coherent multitrack song arrangement plan appropriate to the user's prompt. "
        "Provide a JSON response with the following exact fields: "
        "'title' (string), 'tempo' (integer 40..200), 'bars' (integer 24..128), "
        "'sections' (list of {'name', 'start_bar', 'progression'}) where the first start_bar is 1 and values are strictly increasing, "
        "where 'progression' is a list of four chord names, "
        "'tracks' (list of {'name', 'role', 'channel', 'program', 'pedal_allowed'}), "
        "'key' (string), 'motif' (short original idea description). "
        "Roles may include melody, harmony, bass, drums, and textures depending on the genre. "
        "Programs are General MIDI integers 0..127. "
        "Drums must use channel 9. "
        "Each non-drum track must have a unique channel. "
        "Set pedal_allowed true only for appropriate keyboard tracks. "
        "Ensure the plan includes meaningful repeated sections, development, and an ending. "
        "Do not use rigid fixed lengths or track counts. Do not include copyrighted reference music."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "think": False,
        "format": "json",
        "options": {
            "temperature": 0.5,
            "num_ctx": 8192,
            "num_predict": 2500
        }
    }

    response = core.api('/api/chat', payload, timeout=600)

    if response.get('done_reason') == 'length':
        raise ValueError("Response reached length limit")

    content = response['message']['content']
    return json.loads(content)

def validate_plan(plan):
    try:
        for key in ['title', 'tempo', 'bars', 'key', 'motif', 'sections', 'tracks']:
            if key not in plan: raise KeyError

        if not isinstance(plan['title'], str) or not plan['title'].strip(): raise ValueError
        if not isinstance(plan['key'], str) or not plan['key'].strip(): raise ValueError
        if not isinstance(plan['motif'], str) or not plan['motif'].strip(): raise ValueError

        if not isinstance(plan['tempo'], int) or isinstance(plan['tempo'], bool) or not (40 <= plan['tempo'] <= 200): raise ValueError
        if not isinstance(plan['bars'], int) or isinstance(plan['bars'], bool) or not (24 <= plan['bars'] <= 128): raise ValueError

        sections = plan['sections']
        if not isinstance(sections, list) or len(sections) == 0: raise ValueError
        if sections[0].get('start_bar') != 1: raise ValueError
        prev_bar = 0
        for s in sections:
            if not isinstance(s.get('name'), str) or not s['name'].strip(): raise ValueError
            start = s.get('start_bar')
            if not isinstance(start, int) or isinstance(start, bool) or start <= prev_bar or start > plan['bars']: raise ValueError
            prev_bar = start
            prog = s.get('progression', [])
            if not isinstance(prog, list) or not (1 <= len(prog) <= 8): raise ValueError
            if any(not isinstance(p, str) or not p.strip() for p in prog): raise ValueError

        tracks = plan['tracks']
        if not isinstance(tracks, list) or not (1 <= len(tracks) <= 15): raise ValueError
        names = set()
        channels = set()
        for t in tracks:
            name = t.get('name')
            role = t.get('role')
            chan = t.get('channel')
            prog = t.get('program')
            if not isinstance(name, str) or not name.strip() or name in names: raise ValueError
            names.add(name)
            if not isinstance(role, str) or not role.strip(): raise ValueError
            if not isinstance(chan, int) or isinstance(chan, bool) or not (0 <= chan <= 15): raise ValueError
            if not isinstance(prog, int) or isinstance(prog, bool) or not (0 <= prog <= 127): raise ValueError
            if not isinstance(t.get('pedal_allowed'), bool): raise ValueError

            if (chan == 9) != (role == 'drums'): raise ValueError

            if chan == 9:
                if role != 'drums': raise ValueError
            else:
                if chan in channels: raise ValueError
                channels.add(chan)
            if chan == 9 and 9 not in channels: channels.add(9)

        return plan
    except KeyError:
        raise ValueError("Missing required keys")

def call_notes(model, messages):
    payload = {
        'model': model,
        'messages': messages,
        'stream': False,
        'think': False,
        'format': 'json',
        'options': {
            'temperature': 0.5,
            'num_ctx': 8192,
            'num_predict': 2000
        }
    }
    response = core.api('/api/chat', payload, timeout=600)
    if response.get('done_reason') == 'length':
        raise ValueError('response truncated')
    text = response['message']['content']
    parsed = json.loads(text)
    return (text, parsed)

def compose_block(model, prompt, context, section, track, bars, previous_summary):
    import json

    user_content = json.dumps({
        "prompt": prompt,
        "context": context,
        "section": section,
        "track": track,
        "previous_summary": previous_summary
    })

    bar_ranges = [f"bar {i+1}: beats {i*4} through {(i+1)*4}" for i in range(bars)]

    system_prompt = (
        "Create original editable MIDI for ONE track and THIS section in requested genre. "
        "Explain each bar uses 4 beats; bar i has local beat positions [4*(i-1),4*i). "
        "Require at most " + str(bars) + " bars. "
        "Use " + track['role'] + " appropriate notes and meaningful rests, vary velocities, "
        "preserve motif and fit chord progression, drums use GM percussion. "
        "Use 4/4 and computed local limit: " + str(bars) + " bars end at beat " + str(bars*4) + ", "
        "every note start >=0 and end <= " + str(bars*4) + ". "
        "Require JSON object {'notes':[{'pitch':int,'start':number,'duration':number,'velocity':int}],'summary':str}. "
        "Permit empty notes for rest. User content is json.dumps of prompt, context, section, track and previous_summary. "
        "\n\n" + "\n".join(bar_ranges)
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]

    last_error = None
    for attempt in range(3):
        raw_text = None
        try:
            raw_text, parsed = call_notes(model, messages)

            notes = parsed['notes']
            summary = parsed['summary']

            if not isinstance(notes, list) or not isinstance(summary, str):
                raise ValueError("Invalid structure")

            if notes:
                temp = {**track, "notes": notes}
                validate_track_types([temp], bars * 4)
                corrected, repairs = repair_same_pitch_overlaps(notes)
                parsed['raw_notes'] = notes
                parsed['repairs'] = repairs
                parsed['notes'] = corrected
                temp['notes'] = corrected
                validate_note_intervals([temp], bars * 4)

            return review_block_harmony(model, parsed, track, context['progression'])

        except (ValueError, TypeError, KeyError) as e:
            last_error = str(e)
            retry_msg = (
                f"Error: {last_error}. When notes of the same pitch overlap, move, shorten, "
                f"change pitch, or remove one of the conflicting notes so the earlier note ends "
                f"at or before the next note starts. Use the pitch and times from the error. "
                f"Keep other notes and return the complete JSON. Ensure every note start >=0 and end <= {bars*4}."
            )
            if raw_text is None:
                messages.append({
                    "role": "user",
                    "content": retry_msg
                })
            else:
                messages.append({"role": "assistant", "content": raw_text})
                messages.append({
                    "role": "user",
                    "content": retry_msg
                })
            continue

    raise ValueError(f"Failed after 3 attempts. Last error: {last_error}")
def compose_arrangement(model, prompt, plan, block_fn=None):
    if block_fn is None: block_fn = compose_block
    validate_plan(plan)

    song = {
        "title": plan["title"],
        "tempo": plan["tempo"],
        "bars": plan["bars"],
        "sections": [],
        "tracks": []
    }
    song['harmony_reviews'] = []

    for track_data in plan["tracks"]:
        track = {
            "name": track_data["name"],
            "role": track_data["role"],
            "channel": track_data["channel"],
            "program": track_data["program"],
            "pedal_allowed": track_data["pedal_allowed"],
            "notes": [],
            "controllers": []
        }
        song["tracks"].append(track)

    for section_data in plan["sections"]:
        section = {
            "name": section_data["name"],
            "start_bar": section_data["start_bar"],
            "progression": section_data.get("progression", [])
        }
        song["sections"].append(section)

    track_summaries = {track["name"]: "" for track in song["tracks"]}

    for i, section in enumerate(song["sections"]):
        start_bar = section["start_bar"]
        if i + 1 < len(song["sections"]):
            end_bar = song["sections"][i+1]["start_bar"]
        else:
            end_bar = plan["bars"] + 1

        section_duration = end_bar - start_bar
        current_bar = start_bar

        while current_bar < end_bar:
            block_size = min(4, end_bar - current_bar)

            for track in song["tracks"]:
                # Calculate progression for this specific block
                # Derived by cycling section['progression'] starting from position within section
                relative_pos = current_bar - start_bar
                block_progression = []
                prog_list = section["progression"]
                if prog_list:
                    for b in range(current_bar, current_bar + block_size):
                        idx = (b - start_bar) % len(prog_list)
                        block_progression.append(prog_list[idx])

                context = {
                    'key': plan['key'],
                    'motif': plan['motif'],
                    'progression': block_progression,
                    'start_bar': current_bar,
                    'section_start_bar': start_bar
                }

                track_metadata = {
                    "name": track["name"],
                    "role": track["role"],
                    "channel": track["channel"],
                    "program": track["program"],
                    "pedal_allowed": track["pedal_allowed"]
                }

                print(f"Processing Section: {section['name']}, Bar: {current_bar}, Track: {track['name']}", flush=True)

                result = block_fn(
                    model,
                    prompt,
                    context,
                    section['name'],
                    track_metadata,
                    block_size,
                    track_summaries[track['name']]
                )

                if result is None:
                    raise ValueError("Generation failed")

                if 'harmony_review' in result:
                    song['harmony_reviews'].append({'track': track['name'], 'start_bar': current_bar, 'status': result['harmony_review']['status'], 'warnings': result['harmony_review']['warnings'], 'error': result['harmony_review'].get('error')})

                # Globalize note starts
                for note in result['notes']:
                    global_start = (current_bar - 1) * 4
                    new_note = note.copy()
                    new_note['start'] += global_start
                    track['notes'].append(new_note)

                track_summaries[track['name']] = result['summary']

            current_bar += block_size

    validate_arrangement(song)
    return song
def make_block_cache(directory, block_fn):
    from pathlib import Path
    import hashlib
    import json
    import tempfile
    import os

    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)

    def wrapper(*args):
        key_data = ['v2-harmony-review', *args]
        key = hashlib.sha256(json.dumps(key_data, sort_keys=True, ensure_ascii=False).encode('utf8')).hexdigest()
        target = path / f"{key}.json"

        if target.exists():
            with open(target, 'r', encoding='utf-8') as f:
                result = json.load(f)
        else:
            result = block_fn(*args)

        if not isinstance(result, dict) or 'notes' not in result or 'summary' not in result:
            raise ValueError("Invalid result format")

        notes = result['notes']
        summary = result['summary']
        if not isinstance(summary, str):
            raise ValueError("Summary must be string")

        if not isinstance(notes, list):
            raise ValueError("Notes must be a list")

        if notes:
            track_data = args[4]
            temp_track = track_data.copy()
            temp_track['notes'] = notes
            validate_track_types([temp_track], args[5]*4)
            validate_note_intervals([temp_track], args[5]*4)

        if target.exists():
            return result

        tmp_file = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=str(path), delete=False)
        try:
            json.dump(result, tmp_file)
            tmp_file.flush()
            tmp_file.close()
            os.replace(tmp_file.name, target)
            return result
        except Exception as e:
            if os.path.exists(tmp_file.name):
                os.unlink(tmp_file.name)
            raise e

    return wrapper

def repair_same_pitch_overlaps(notes):
    new_notes = []
    for i, note in enumerate(notes):
        new_notes.append({
            'pitch': note['pitch'],
            'start': note['start'],
            'duration': note['duration'],
            'velocity': note['velocity'],
            'original_index': i
        })

    groups = {}
    for note in new_notes:
        p = note['pitch']
        if p not in groups:
            groups[p] = []
        groups[p].append(note)

    for p in groups:
        groups[p].sort(key=lambda x: (x['start'], x['original_index']))

    repairs = []
    for p in groups:
        group = groups[p]
        for i in range(len(group) - 1):
            current = group[i]
            next_note = group[i+1]

            if current['start'] == next_note['start']:
                raise ValueError('same pitch starts at same time')

            if current['start'] + current['duration'] > next_note['start']:
                old_dur = current['duration']
                new_dur = next_note['start'] - current['start']

                if new_dur <= 0:
                    # This case is technically covered by the same start check,
                    # but included for logical completeness.
                    raise ValueError('same pitch starts at same time')

                if round(next_note['start'] * 480) <= round(current['start'] * 480): raise ValueError('trimmed note is zero MIDI ticks')

                current['duration'] = new_dur
                repairs.append({
                    'pitch': p,
                    'start': current['start'],
                    'old_duration': old_dur,
                    'new_duration': new_dur
                })

    sorted_notes = sorted(new_notes, key=lambda x: x['original_index'])
    # Remove the helper key before returning
    for n in sorted_notes:
        del n['original_index']

    return (sorted_notes, repairs)


def prepare_run(prompt, model, resume_dir=None):
    from pathlib import Path
    import uuid
    run = Path(resume_dir) if resume_dir is not None else core.ORG/'music'/('song-'+uuid.uuid4().hex)
    try:
        if resume_dir is None:
            run.mkdir(parents=True, exist_ok=False)
            core.dump(run / 'request.json', {'prompt': prompt, 'model': model})
        else:
            request_data = json.loads((run / 'request.json').read_text(encoding='utf-8'))
            if request_data['prompt'] != prompt or request_data['model'] != model:
                raise ValueError("Prompt or model mismatch")

        print(f'Run directory: {run}', flush=True)
        print('Keep this path to resume if generation stops.', flush=True)

        if (run / 'plan.json').exists():
            plan = json.loads((run / 'plan.json').read_text(encoding='utf-8'))
        else:
            plan = make_plan(prompt, model)
            for track in plan.get('tracks', []):
                track.setdefault('pedal_allowed', False)
            validate_plan(plan)
            core.dump(run / 'plan.json', plan)

        validate_plan(plan)
        return run, plan
    except Exception as e:
        raise ValueError(f'Run {run}: {e}') from e


def run_song(prompt, model, resume_dir=None):
    import os
    core.local_model(model)
    run, plan = prepare_run(prompt, model, resume_dir)
    try:
        if (run / 'composition.mid').exists():
            raise ValueError('output already exists')
        callback = make_block_cache(run / 'blocks', compose_block)
        song = compose_arrangement(model, prompt, plan, block_fn=callback)
        report = validate_arrangement(song)

        revised_count = sum(1 for r in song["harmony_reviews"] if r["status"] == "revised")
        failed_count = sum(1 for r in song["harmony_reviews"] if r["status"] == "review_failed")
        flagged_blocks = [r for r in song["harmony_reviews"] if r.get("warnings") or r["status"] == "review_failed"]

        report["harmony_review"] = {
            "revised_blocks": revised_count,
            "failed_blocks": failed_count,
            "flagged_blocks": flagged_blocks
        }

        print(f"Revised: {revised_count}, Failed: {failed_count}, Flagged: {len(flagged_blocks)}", flush=True)

        core.dump(run / 'composition.json', song)
        core.dump(run / 'validation.json', report)
        temporary = run / 'composition.mid.part'
        write_arrangement(song, temporary)
        os.replace(temporary, run / 'composition.mid')
        return run
    except Exception as e:
        raise ValueError(f'Run {run}: {e}') from e
def check_block_harmony(notes, track, progression):
    if track.get('role') not in ('bass', 'harmony'):
        return []

    messages = []
    tolerance = 1e-6

    for note in notes:
        start = note['start']
        # Check if start is on a bar downbeat (0, 4, 8, ...)
        if abs(start % 4) < tolerance or abs((start % 4) - 4) < tolerance:
            bar_index = int(round(start / 4))

            if bar_index >= len(progression):
                raise ValueError("Progression index out of range")

            chord_label = progression[bar_index]
            try:
                chord_data = chord(chord_label)
            except ValueError:
                raise ValueError(f"Unsupported chord label: {chord_label}")

            allowed_pcs = chord_data['pitch_classes']

            pitch = note['pitch']
            pc = pitch % 12
            if pc not in allowed_pcs:
                bar_num = (bar_index + 1)
                msg = f"Bar {bar_num} {chord_label}: pitch {pitch} (pc {pc}) not in {allowed_pcs}"
                messages.append(msg)

    return messages


def harmony_facts(progression, notes):
    if not notes:
        return []

    lo = max(0, min(note['pitch'] for note in notes) - 12)
    hi = min(127, max(note['pitch'] for note in notes) + 12)

    results = []
    for bar_idx, label in enumerate(progression, 1):
        chord_data = chord(label)
        allowed_classes = set(chord_data['pitch_classes'])

        allowed_midi = []
        for p in range(lo, hi + 1):
            if (p % 12) in allowed_classes:
                allowed_midi.append(p)

        results.append({
            'bar': bar_idx,
            'beat': (bar_idx - 1) * 4,
            'chord': label,
            'allowed_midi': allowed_midi
        })

    return results


def review_block_harmony(model, parsed, track, progression):
    before = []
    try:
        before = check_block_harmony(parsed['notes'], track, progression)

        if len(before) < 2:
            return {**parsed, 'harmony_review': {'status': 'not_requested', 'warnings': before}}

        facts = harmony_facts(progression, parsed['notes'])

        messages = [
            {"role": "system", "content": "You must return a JSON object with top-level keys 'notes' and 'summary'. The 'notes' key must contain the COMPLETE list of note objects with 'pitch', 'start', 'duration', and 'velocity'. Review each flagged downbeat against allowed_midi while preserving the part's original register. Note that a flagged downbeat may be an intentional suspension or other non-chord tone; preserve it if musically justified rather than forcing a change. Non-downbeat non-chord tones may be intentional. Keep note count, order, starts, durations, and velocities exactly the same. You may change pitches to better support the chords."},
            {"role": "user", "content": json.dumps({
                "original": parsed,
                "chords": facts,
                "warnings": before
            })}
        ]

        _, candidate = call_notes(model, messages)
        candidate_notes = candidate['notes']

        if len(candidate_notes) != len(parsed['notes']):
            raise ValueError("Note count mismatch")

        for i in range(len(parsed['notes'])):
            n1 = parsed['notes'][i]
            n2 = candidate_notes[i]
            if n1['start'] != n2['start'] or n1['duration'] != n2['duration'] or n1['velocity'] != n2['velocity']:
                raise ValueError("Timing or velocity mismatch")
            if abs(n1['pitch'] - n2['pitch']) > 12:
                raise ValueError("Pitch change too large")

        temp = {**track, 'notes': candidate_notes}
        validate_track_types([temp], len(progression) * 4)
        validate_note_intervals([temp], len(progression) * 4)

        after = check_block_harmony(candidate_notes, track, progression)

        if len(after) < len(before):
            return {
                **parsed,
                'notes': candidate_notes,
                'harmony_review': {
                    'status': 'revised',
                    'original_notes': parsed['notes'],
                    'warnings': after
                }
            }
        else:
            return {
                **parsed,
                'harmony_review': {
                    'status': 'unchanged',
                    'warnings': before
                }
            }

    except (ValueError, KeyError, TypeError) as e:
        return {
            **parsed,
            'harmony_review': {
                'status': 'review_failed',
                'warnings': before,
                'error': str(e)
            }
        }
