# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Exact raw-event diffs for Logic editing; these do not prove native region ownership."""
from copy import deepcopy
import re

EVENT_FILTERS = ('aftertouch', 'controller', 'noteEvents', 'pitchBend',
                 'polyAftertouch', 'programChange', 'systemExclusive')


def checked_rows(snapshot):
    """Require a stable, unfiltered English Event List observation.

    Count agreement is necessary, not proof of generic traversal or ownership.
    Caller must separately establish the native project/region binding.
    """
    if (snapshot.get('success') is not True
        or snapshot.get('observed_rows_content_stable') is not True
        or snapshot.get('row_selection_restored') is not True):
        raise ValueError('Stable event observation with restored selection is required')
    filters = snapshot.get('event_list_filter_states') or {}
    if any(filters.get(key) is not True for key in EVENT_FILTERS):
        raise ValueError('All event type filters must be visible and verified')
    rows = snapshot.get('raw_rows')
    count = re.fullmatch(r'(0|[1-9][0-9]*) Events?', snapshot.get('event_list_item_count_text', ''))
    if not isinstance(rows, list) or not count or int(count[1]) != len(rows):
        raise ValueError('Event count does not match the observed rows')
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError('Malformed event row')
    return rows


def expected_pitch_edit(snapshot, row_index, from_pitch, to_pitch):
    """Produce the exact allowed diff; refuse stale/ambiguous numeric targets."""
    rows = checked_rows(snapshot)
    if (type(row_index) is not int or not 0 <= row_index < len(rows)
        or any(type(p) is not int or not 0 <= p <= 127 for p in (from_pitch, to_pitch))
        or from_pitch == to_pitch):
        raise ValueError('One explicit note pitch change is required')
    row = rows[row_index]
    if (row.get('Status', {}).get('value_description') != 'Note'
        or row.get('Num', {}).get('slider_value') != from_pitch):
        raise ValueError('Selected row is not the expected note')
    expected = deepcopy(rows)
    expected[row_index]['Num']['slider_value'] = to_pitch
    return expected


def verify_pitch_edit(before, after, row_index, from_pitch, to_pitch):
    """Permit only the requested pitch field; preserve every other raw field.

    No timing conversion or deduplication: duplicate notes and CC64 ordering are
    retained. A failure never authorizes save or a blind retry.
    """
    expected = expected_pitch_edit(before, row_index, from_pitch, to_pitch)
    actual = checked_rows(after)
    for field in ('selected_region_observation', 'event_list_region_path', 'live_header_titles'):
        if not before.get(field) or before[field] != after.get(field):
            raise ValueError('Region or Event List context changed')
    if actual != expected:
        raise ValueError('Unexpected event changes; do not save or retry automatically')
    return {'exact_requested_pitch_diff': True, 'other_raw_fields_preserved': True,
            'event_count': len(actual), 'canonical_owner_or_completeness_proven': False}


def verify_region_shift(before, after, bars):
    """Verify a whole-bar shift of every event, including all controller events.

    This verifier does not authorize a move actuator. It accepts only matching
    region identity/bounds and an exact shift in the displayed BBT positions;
    pitch, duration, flags, channel, values, event order and count must survive.
    Native target/focus custody and meter qualification belong to the caller.
    """
    if type(bars) is not int or bars == 0:
        raise ValueError('A nonzero integer bar shift is required')
    old = checked_rows(before); new = checked_rows(after)
    original_region = before.get('selected_region_observation', {})
    expected_region = deepcopy(original_region)
    for field in ('start_bar','end_bar'):
        value = expected_region.get(field)
        if type(value) is not int or value + bars < 1:
            raise ValueError('Region bar boundaries are unavailable')
        expected_region[field] = value + bars
    if not original_region.get('name') or after.get('selected_region_observation') != expected_region:
        raise ValueError('Moved region does not match the intended identity and bounds')
    for field in ('event_list_region_path','live_header_titles'):
        if not before.get(field) or before[field] != after.get(field):
            raise ValueError('Event List context changed during region move')
    if len(old) != len(new):
        raise ValueError('Region move changed the event count')
    for first, second in zip(old, new):
        expected = deepcopy(first)
        for row in (first, second):
            text = row.get('Position', {}).get('value_description', '')
            if not re.fullmatch(r'\s*[1-9][0-9]*(?:\s+[1-9][0-9]*){3}\s*', text):
                raise ValueError('Event position is unavailable')
        old_position = list(map(int,first['Position']['value_description'].split()))
        new_position = list(map(int,second['Position']['value_description'].split()))
        old_position[0] += bars
        if old_position != new_position:
            raise ValueError('An event did not move by the requested number of bars')
        # Accept formatting changes to the observed position only, checking all
        # values independently before comparing the rest of the raw row.
        expected['Position']['value_description'] = second['Position']['value_description']
        if 'group_slider_values' in expected['Position']:
            initial = first['Position']['group_slider_values']
            if not isinstance(initial,list) or len(initial)!=4 or initial != list(map(int,first['Position']['value_description'].split())):
                raise ValueError('Position components disagree')
            expected['Position']['group_slider_values'] = old_position
        if second != expected:
            raise ValueError('A non-position event field changed during the region move')
    return {'exact_requested_bar_shift':True,'event_count':len(new),
            'other_raw_fields_preserved':True,'canonical_owner_or_completeness_proven':False}
