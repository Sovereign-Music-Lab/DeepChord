# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Narrow SMF proof-of-concept; not a Logic region editor.

Transpose one whole SMF track without rewriting timestamps, controllers, or
other event bytes. This does not establish project or region identity.
"""
import struct


def _vlq(data, pos, end):
    value=0
    for _ in range(4):
        if pos>=end:raise ValueError('Truncated variable-length quantity')
        b=data[pos];pos+=1;value=(value<<7)|(b&127)
        if not b&128:return value,pos
    raise ValueError('Oversized variable-length quantity')


def transpose_track_bytes(data, track_index, semitones):
    """Return (new bytes, evidence); only note pitch bytes may differ."""
    if not isinstance(data,bytes) or len(data)<14 or data[:4]!=b'MThd':raise ValueError('Invalid MIDI header')
    header_len=struct.unpack_from('>I',data,4)[0]
    if header_len!=6:raise ValueError('Unsupported MIDI header')
    fmt,count,division=struct.unpack_from('>HHH',data,8)
    if fmt not in (0,1) or division==0 or division&0x8000:raise ValueError('Unsupported MIDI format or timebase')
    if isinstance(track_index,bool) or not isinstance(track_index,int) or not 0<=track_index<count:raise ValueError('Invalid track index')
    if isinstance(semitones,bool) or not isinstance(semitones,int) or not -24<=semitones<=24 or semitones==0:raise ValueError('Invalid transposition')
    chunks=[];pos=14
    for _ in range(count):
        if pos+8>len(data) or data[pos:pos+4]!=b'MTrk':raise ValueError('Invalid track chunk')
        length=struct.unpack_from('>I',data,pos+4)[0];start=pos+8;end=start+length
        if end>len(data):raise ValueError('Truncated track')
        chunks.append((start,end));pos=end
    if pos!=len(data):raise ValueError('Unexpected trailing data')
    out=bytearray(data);start,end=chunks[track_index];pos=start;running=None;active=set();edited=[];pedal=[];tick=0;ended=False
    while pos<end:
        delta,pos=_vlq(data,pos,end);tick+=delta
        if pos>=end:raise ValueError('Truncated event')
        b=data[pos]
        if b&128:
            status=b;pos+=1
            if status<0xf0:running=status
            else:running=None
        elif running is not None:status=running
        else:raise ValueError('Missing running status')
        if status==0xff:
            if pos>=end:raise ValueError('Truncated meta event')
            kind=data[pos];pos+=1;length,pos=_vlq(data,pos,end)
            if pos+length>end:raise ValueError('Truncated meta payload')
            pos+=length
            if kind==0x2f:
                if length!=0 or pos!=end:raise ValueError('Invalid end-of-track')
                ended=True
            continue
        if status in (0xf0,0xf7):
            length,pos=_vlq(data,pos,end)
            if pos+length>end:raise ValueError('Truncated SysEx')
            pos+=length;continue
        if status>=0xf0:raise ValueError('Unsupported MIDI system event')
        kind=status&0xf0;channel=status&15;size=1 if kind in (0xc0,0xd0) else 2
        if pos+size>end or any(x&128 for x in data[pos:pos+size]):raise ValueError('Invalid channel event')
        a=data[pos];b=data[pos+1] if size==2 else None
        if kind==0xb0 and a==64:pedal.append((tick,channel,b))
        if kind in (0x80,0x90):
            key=(channel,a);on=kind==0x90 and b!=0
            if on:
                if key in active:raise ValueError('Overlapping same-pitch notes are ambiguous')
                active.add(key)
            elif key not in active:raise ValueError('Unmatched note off')
            else:active.remove(key)
            new=a+semitones
            if not 0<=new<=127:raise ValueError('Transposition exceeds MIDI range')
            out[pos]=new;edited.append(pos)
        pos+=size
    if not ended or active or not edited:raise ValueError('Incomplete track or no notes')
    return bytes(out),{'edited_pitch_bytes':len(edited),'pedal_events':pedal,'ppq':division,'track_index':track_index}
