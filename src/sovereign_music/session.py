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
    project_path=getattr(args,'logic_project',None)
    if project_path and (not args.mcp_config or args.logic):raise ValueError('--logic-project requires --mcp-config and cannot be combined with --logic')
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
        new_success=False
        while True:
            if queued:request=queued.pop(0)
            elif not interactive:break
            else:
                try:request=input_fn('composer> ').strip()
                except (EOFError,KeyboardInterrupt):break
            if not request:continue
            if request=='/quit':break
            if request=='/status':output(json.dumps(state,ensure_ascii=False,indent=2));continue
            if request=='/new':state['latest_run']=None;new_success=False;save();output('Next request starts a new piece. Earlier versions remain saved.');continue
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
            new_success=False
            turn={'request':request,'previous_run':state['latest_run'],'status':'running','model':args.model,'adapter':str(args.adapter) if args.adapter else None}
            state['turns'].append(turn);save()
            try:
                a=argparse.Namespace(prompt=request,bars=args.bars,model=args.model,adapter=args.adapter,previous_run=state['latest_run'],theory_model=getattr(args,'theory_model',None),theory_adapter=getattr(args,'theory_adapter',None))
                result=core.compose(a);turn.update(status='composed',run=str(result));state['latest_run']=str(result);save()
                new_success=True
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
        if project_path:
            if not new_success:
                state['logic_build']={'status':'skipped','error':'No successful final request in this session'};save()
                raise RuntimeError('Logic project not built: the final request did not succeed')
            from .logic import build_project
            try:
                state['logic_build']=build_project(state['latest_run'],project_path,args.mcp_config)
                output('Logic project saved: '+str(project_path))
            except (ValueError,OSError,RuntimeError,TimeoutError,subprocess.SubprocessError) as e:
                state['logic_build']={'status':'failed','error':str(e)};save()
                raise RuntimeError('Logic project incomplete: '+str(e)) from e
            save()
        return state
    finally:
        if not handle.closed:handle.close()
        lock.unlink()
