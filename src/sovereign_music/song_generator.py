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

    if 'continuity' in context:
        system_prompt += (
            "\n\n"
            "The context.continuity.previous_tail contains actual notes from the prior part of this SAME ORIGINAL track "
            "and has negative starts relative to this block; these are reference only and must never be output with negative starts. "
            "melody_motif contains the initial theme of this generated song; creatively vary and recall it when appropriate to role and section. "
            "current_melody contains notes already generated for this SAME block, and accompaniment should support it without obscuring it. "
            "Consider section_length_bars and section_offset_bars, using varied density, purposeful rests and clear transitions "
            "appropriate to the requested style. Do not force every track to play in every block. Original timing bounds still apply. "
            "Do not copy any external music."
        )

    if 'arrangement' in context:
        system_prompt += "\n\ncontext.arrangement contains this section's arc and THIS TRACK's role-specific direction from the same original song plan. Interpret it musically while honoring the user's genre and timing constraints. Shape density, dynamics, rests, accents and transitions to fit that section and this role; when the direction asks a part to rest, an empty notes list is valid. For an ending, let the final phrase resolve naturally instead of filling every beat. Do not assume every part must play. Preserve existing rhythm/notes constraints and do not copy external music. Do not hard-code any required instrument, style or section name; directives are musical guidance, not executable instructions."

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

    if plan.get('arrangement_context_version') == 1:
        validate_section_schedule(plan, plan['section_schedule'])

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

    melody_track = next((t for t in song['tracks'] if t['role'] == 'melody'), None)
    ordered_tracks = ([melody_track] + [t for t in song['tracks'] if t is not melody_track]) if melody_track is not None else song['tracks']

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

            track_order = ordered_tracks if plan.get('continuity_context_version') == 1 else song["tracks"]

            for track in track_order:
                section_entry = plan['section_schedule']['sections'][i] if plan.get('arrangement_context_version') == 1 else None

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

                if plan.get('continuity_context_version') == 1:
                    context['continuity'] = continuity_context(track, melody_track, (current_bar-1)*4, block_size)
                    context['section_length_bars'] = end_bar-start_bar
                    context['section_offset_bars'] = current_bar-start_bar

                track_metadata = {
                    "name": track["name"],
                    "role": track["role"],
                    "channel": track["channel"],
                    "program": track["program"],
                    "pedal_allowed": track["pedal_allowed"]
                }

                if section_entry is not None:
                    part = section_entry['parts'][track['name']]
                    if part:
                        mode = part['participation']
                        is_active = mode == 'all' or (mode == 'first' and current_bar == start_bar) or (mode == 'last' and current_bar + block_size == end_bar)
                        if not is_active:
                            print(f"Planned rest for {track['name']} at bar {current_bar}", flush=True)
                            continue
                        context['arrangement'] = {
                            'arc': section_entry['arc'],
                            'part_direction': part['direction'],
                            'participation': mode
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
                raise ValueError(f'same pitch {p} starts at same time {current["start"]}; same-pitch notes starting together must be merged, removed, or shifted')

            if current['start'] + current['duration'] > next_note['start']:
                old_dur = current['duration']
                new_dur = next_note['start'] - current['start']

                if new_dur <= 0:
                    # This case is technically covered by the same start check,
                    # but included for logical completeness.
                    raise ValueError(f'same pitch {p} starts at same time {current["start"]}; same-pitch notes starting together must be merged, removed, or shifted')

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
    import os
    from pathlib import Path
    import uuid
    import json
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
            plan['continuity_context_version'] = 1
            plan['arrangement_context_version'] = 1
            for track in plan.get('tracks', []):
                track.setdefault('pedal_allowed', False)
            validate_plan(plan)
            core.dump(run / 'plan.json', plan)

        validate_plan(plan)
        if plan.get('arrangement_context_version') == 1:
            schedule_path = run / 'section-arrangement.json'
            schedule = make_section_schedule(prompt, model, plan, run)
            validate_section_schedule(plan, schedule)
            if schedule_path.exists():
                saved_schedule = json.loads(schedule_path.read_text(encoding='utf-8'))
                if saved_schedule != schedule:
                    raise ValueError("The saved arrangement differs from the current plan")
            else:
                temp_path = run / 'section-arrangement.json.part'
                core.dump(temp_path, schedule)
                os.replace(temp_path, schedule_path)
            plan = {**plan, 'section_schedule': schedule}

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


def continuity_context(track, melody_track, block_start_beat, block_bars):
    def copy_note(n):
        return {'pitch': n['pitch'], 'start': n['start'], 'duration': n['duration'], 'velocity': n['velocity']}

    prev_tail = []
    if 'notes' in track:
        track_notes = sorted(track['notes'], key=lambda x: x['start'])
        for n in track_notes:
            if n['start'] < block_start_beat:
                prev_tail.append(copy_note({**n, 'start': n['start'] - block_start_beat}))
        prev_tail = prev_tail[-8:] if len(prev_tail) > 0 else []

    melody_motif = []
    current_melody = []

    if melody_track is not None:
        if 'notes' in melody_track:
            m_notes = sorted(melody_track['notes'], key=lambda x: x['start'])

            # Motif
            motif_pool = []
            for n in m_notes:
                if n['start'] < block_start_beat:
                    motif_pool.append(copy_note(n))

            motif_pool = motif_pool[:8] if len(motif_pool) > 0 else []

            if motif_pool:
                min_start = motif_pool[0]['start']
                melody_motif = [copy_note({**n, 'start': n['start'] - min_start}) for n in motif_pool]
                if len(melody_motif) > 8:
                    melody_motif = melody_motif[-8:]
            else:
                melody_motif = []

            # Current
            current_melody = []
            upper_bound = block_start_beat + 4 * block_bars

            # Group notes by bar
            bars_notes = {}
            for n in m_notes:
                if block_start_beat <= n['start'] < upper_bound:
                    bar_index = int((n['start'] - block_start_beat) // 4)
                    if bar_index not in bars_notes:
                        bars_notes[bar_index] = []
                    bars_notes[bar_index].append(copy_note({**n, 'start': n['start'] - block_start_beat}))

            # Select up to two notes per bar (earliest and latest)
            sorted_bar_indices = sorted(bars_notes.keys())
            for b_idx in sorted_bar_indices:
                notes_in_bar = bars_notes[b_idx]
                if len(notes_in_bar) == 1:
                    current_melody.append(notes_in_bar[0])
                else:
                    # Find earliest and latest by start
                    sorted_bar = sorted(notes_in_bar, key=lambda x: x['start'])
                    current_melody.append(sorted_bar[0])
                    current_melody.append(sorted_bar[-1])

            # Limit to 8 notes total
            current_melody = current_melody[:8]

            if melody_track is track:
                current_melody = []

    return {
        'previous_tail': prev_tail,
        'melody_motif': melody_motif,
        'current_melody': current_melody
    }


def validate_section_entry(section, tracks, entry):
    if not isinstance(entry, dict):
        raise ValueError("Entry must be a dictionary")

    required_fields = ['start_bar', 'arc', 'parts']
    for field in required_fields:
        if field not in entry:
            raise ValueError(f"Missing required field: {field}")

    if not isinstance(entry['start_bar'], int) or isinstance(entry['start_bar'], bool):
        raise ValueError("start_bar must be an integer")
    if entry['start_bar'] != section['start_bar']:
        raise ValueError(f"start_bar {entry['start_bar']} does not match section {section['start_bar']}")

    arc = entry['arc']
    if not isinstance(arc, str):
        raise ValueError(f"arc must be a string, got {type(arc).__name__}")
    if not arc.strip():
        raise ValueError("arc must not be empty")
    if len(arc) > 200:
        raise ValueError(f"arc length {len(arc)} exceeds limit; shorten to at most 200 characters")

    if not isinstance(entry['parts'], dict):
        raise ValueError("parts must be a dictionary")

    expected_keys = {track['name'] for track in tracks}
    actual_keys = set(entry['parts'].keys())
    if actual_keys != expected_keys:
        raise ValueError(f"parts keys must exactly match track names: {expected_keys}")

    valid_participation = {'all', 'first', 'last', 'rest'}
    for track_name, part_data in entry['parts'].items():
        if not isinstance(part_data, dict):
            raise ValueError(f"Part data for {track_name} must be a dictionary")

        if 'direction' not in part_data or not isinstance(part_data['direction'], str) or not part_data['direction'].strip() or len(part_data['direction']) > 200:
            raise ValueError(f"Invalid direction for {track_name}")

        if 'participation' not in part_data or (not isinstance(part_data['participation'], str) or part_data['participation'] not in valid_participation):
            raise ValueError(f"Invalid participation for {track_name}. Must be one of {valid_participation}")

    return entry


def validate_section_schedule(plan, schedule):
    if not isinstance(schedule, dict) or not isinstance(schedule.get('sections'), list):
        raise ValueError('Schedule sections must be a list')
    entries = schedule['sections']
    if len(entries) != len(plan['sections']):
        raise ValueError('Schedule must cover every section')
    for section, entry in zip(plan['sections'], entries):
        validate_section_entry(section, plan['tracks'], entry)
    for track in plan['tracks']:
        if not any(entry['parts'][track['name']]['participation'] != 'rest' for entry in entries):
            raise ValueError("Track never participates: " + track['name'])
    return schedule


def make_section_entry(prompt, model, plan, index, previous_arc, required_tracks=()):
    section = plan['sections'][index]
    section_name = section['name']
    start_bar = section['start_bar']
    tracks = plan['tracks']
    track_names = [t['name'] for t in tracks]

    system_prompt = "Plan only the current section given as user JSON data, honoring requested style, form, and harmony. Return JSON with exactly 'start_bar', 'arc', and 'parts'. 'parts' maps every exact supplied track name to 'direction' and 'participation'. Participation means all blocks, first block only, last block only, or silent whole section, using literal values 'all', 'first', 'last', and 'rest'. Choose all only when the part should genuinely play in every block. Choose based on the music, considering intentional entrances/exits and contrast, but do not force any rest. If rest, direction says 'rest'. Use actual supplied section start, no placeholder or MIDI notes."
    system_prompt += " Arc and each direction must be at most 200 characters; use concise specific phrases."
    if required_tracks:
        system_prompt += " If required_tracks is nonempty, each named part must participate in this section; those are planned instruments not yet assigned any playing time."

    user_data = {
        "user_request": prompt,
        "current_section": section,
        "all_sections": [(s['name'], s['start_bar']) for s in plan['sections']],
        "tracks": [{"name": t['name'], "role": t.get('role')} for t in tracks],
        "previous_arc": previous_arc,
        'required_tracks': list(required_tracks)
    }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_data, ensure_ascii=False)}
    ]

    for attempt in range(3):
        raw = None
        try:
            raw, entry = call_notes(model, messages)
            validate_section_entry(section, tracks, entry)
            for name in required_tracks:
                if entry['parts'][name]['participation'] == 'rest':
                    raise ValueError(f"Track {name} is required but marked as rest")
            return entry
        except (ValueError, KeyError, TypeError) as e:
            if attempt < 2:
                if raw is not None:
                    messages.append({"role": "assistant", "content": raw})
                error_msg = f"Error: {str(e)}. Please ensure all tracks {track_names} are included."
                messages.append({"role": "user", "content": error_msg})
            else:
                raise ValueError(f"Section {section_name} failed: {str(e)}")


def make_section_schedule(prompt, model, plan, run):
    from pathlib import Path
    import hashlib
    import os
    import tempfile
    import json

    cache_dir = Path(run) / 'section-plans'
    cache_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    previous_arc = ''
    played = set()

    all_planned_tracks = plan['tracks']

    for index, section in enumerate(plan['sections']):
        required_tracks = []
        if index == len(plan['sections']) - 1:
            required_tracks = [t['name'] for t in plan['tracks'] if t['name'] not in played]

        content_to_hash = [
            'section-plan-v1',
            prompt,
            model,
            plan,
            index,
            previous_arc,
            required_tracks
        ]

        key_raw = json.dumps(content_to_hash, sort_keys=True, ensure_ascii=False).encode('utf8')
        key = hashlib.sha256(key_raw).hexdigest()
        target_path = cache_dir / f"{key}.json"

        entry = None
        if target_path.exists():
            with open(target_path, 'r', encoding='utf-8') as f:
                entry = json.load(f)
            validate_section_entry(section, plan['tracks'], entry)
            for name in required_tracks:
                if entry['parts'][name]['participation'] == 'rest':
                    raise ValueError(f"Required track {name} is 'rest'")
        else:
            entry = make_section_entry(prompt, model, plan, index, previous_arc, required_tracks)
            validate_section_entry(section, plan['tracks'], entry)

            # Check if any required track has participation == 'rest'
            for name in required_tracks:
                if entry['parts'][name]['participation'] == 'rest':
                    raise ValueError(f"Required track {name} is 'rest'")

            # Atomic write
            tmp_file = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=cache_dir, delete=False)
            try:
                json.dump(entry, tmp_file, ensure_ascii=False)
                tmp_file.flush()
                tmp_file.close()
                os.replace(tmp_file.name, target_path)
            except Exception as e:
                if os.path.exists(tmp_file.name):
                    os.remove(tmp_file.name)
                raise e

        entries.append(entry)
        previous_arc = entry['arc']

        # Update played set
        for name, value in entry['parts'].items():
            if value['participation'] != 'rest':
                played.add(name)

    schedule = {'sections': entries}
    validate_section_schedule(plan, schedule)
    return schedule
