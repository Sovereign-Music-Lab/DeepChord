# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Persistent human-request loop; each accepted revision gets a separate run."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from . import core


def run(args,input_fn=input,output=print):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',args.name):raise ValueError('Session name: 1..64 letters, digits, underscore or hyphen')
    if args.logic and __import__('sys').platform!='darwin':raise ValueError('Logic runs on a Mac. Use MIDI export on this OS, or transfer runs to a Mac.')
    folder=core.ORG/'sessions'/args.name;folder.mkdir(parents=True,exist_ok=True)
    lock=folder/'active.lock'
    try:handle=lock.open('x')
    except FileExistsError:raise ValueError('Session is already active, or a previous process left active.lock. Inspect the process before removing its lock.')
    try:
        handle.write(str(__import__('os').getpid()));handle.close()
        path=folder/'session.json'
        state=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'version':1,'name':args.name,'turns':[],'latest_run':None}
        def save():
            temp=path.with_suffix('.tmp');core.dump(temp,state);temp.replace(path)
        save()
        output('Human → local LLM ↔ theory RAG / chord dictionary (+ optional trained adapter) → MIDI / Logic → human')
        output('/quit /status /explain /new /open. Enter another request to revise; prior versions remain saved.')
        queued=list(getattr(args,'request',[]) or [])
        interactive=not queued
        while True:
            if queued:request=queued.pop(0)
            elif not interactive:break
            else:
                try:request=input_fn('composer> ').strip()
                except (EOFError,KeyboardInterrupt):break
            if not request:continue
            if request=='/quit':break
            if request=='/status':output(json.dumps(state,ensure_ascii=False,indent=2));continue
            if request=='/new':state['latest_run']=None;save();output('Next request starts a new piece. Earlier versions remain saved.');continue
            if request=='/explain':
                if state['latest_run']:output((Path(state['latest_run'])/'EXPLANATION.md').read_text(encoding='utf-8'))
                else:output('No successful version yet.')
                continue
            if request=='/open':
                if not state['latest_run']:output('No successful version yet.');continue
                try:
                    from .logic import open_run
                    output(json.dumps(open_run(state['latest_run'],args.mcp_config),ensure_ascii=False,indent=2))
                except (ValueError,OSError,RuntimeError,TimeoutError) as e:output('Handoff incomplete: '+str(e))
                continue
            if request.startswith('/'):output('Unknown command; use /quit /status /explain /new /open.');continue
            turn={'request':request,'previous_run':state['latest_run'],'status':'running','model':args.model,'adapter':str(args.adapter) if args.adapter else None}
            state['turns'].append(turn);save()
            try:
                a=argparse.Namespace(prompt=request,bars=args.bars,model=args.model,adapter=args.adapter,previous_run=state['latest_run'],theory_model=getattr(args,'theory_model',None),theory_adapter=getattr(args,'theory_adapter',None))
                result=core.compose(a);turn.update(status='composed',run=str(result));state['latest_run']=str(result);save()
                # Explain first: a DAW failure must not discard a valid composition.
                output((result/'EXPLANATION.md').read_text(encoding='utf-8'))
                output('Editable source: '+str(result))
                if args.logic:
                    from .logic import open_run
                    try:turn['logic']=open_run(result,args.mcp_config)
                    except (ValueError,OSError,RuntimeError,TimeoutError) as e:turn['logic_error']=str(e);output('Handoff incomplete: '+str(e))
            except KeyboardInterrupt:
                turn.update(status='interrupted');save();break
            except (ValueError,KeyError,TypeError,OSError,RuntimeError,TimeoutError,ImportError,subprocess.SubprocessError) as e:
                turn.update(status='failed',error=str(e));output('Request failed; previous successful version retained. '+str(e))
            save()
        return state
    finally:
        if not handle.closed:handle.close()
        lock.unlink()
