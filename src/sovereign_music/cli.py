# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from . import core


def parser():
    p=argparse.ArgumentParser(prog='deepchord',description='DeepChord by Sovereign Music Lab — local composition, Logic, and private LoRA')
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('doctor')
    q=sub.add_parser('rag');q.add_argument('query')
    c=sub.add_parser('compose');c.add_argument('prompt');c.add_argument('--bars',type=int,choices=range(1,17),default=8);c.add_argument('--model',default=core.MODEL);c.add_argument('--adapter',type=Path);c.add_argument('--logic',action='store_true');c.add_argument('--mcp-config',type=Path)
    d=sub.add_parser('demo');d.add_argument('--out',type=Path,required=True)
    v=sub.add_parser('validate');v.add_argument('file',type=Path)
    f=sub.add_parser('feedback');f.add_argument('run',type=Path);f.add_argument('--rating',type=int,choices=range(1,6),required=True);f.add_argument('--note',required=True)
    l=sub.add_parser('logic');ls=l.add_subparsers(dest='action',required=True)
    li=ls.add_parser('inspect');li.add_argument('--mcp-config',type=Path,required=True)
    lo=ls.add_parser('open');lo.add_argument('run',type=Path);lo.add_argument('--mcp-config',type=Path)
    t=sub.add_parser('train');ts=t.add_subparsers(dest='action',required=True)
    tp=ts.add_parser('prepare');tp.add_argument('source',type=Path);tp.add_argument('--out',type=Path,required=True)
    td=ts.add_parser('smoke-data');td.add_argument('--out',type=Path,required=True)
    tr=ts.add_parser('run');tr.add_argument('--model',type=Path,required=True);tr.add_argument('--data',type=Path,required=True);tr.add_argument('--out',type=Path,required=True);tr.add_argument('--iters',type=int,default=100)
    tg=ts.add_parser('generate');tg.add_argument('prompt');tg.add_argument('--model',type=Path,required=True);tg.add_argument('--adapter',type=Path,required=True);tg.add_argument('--max-tokens',type=int,default=512)
    return p


def demo(out):
    song={'title':'Original installation check','tempo':76,'bars':2,'chords':['G7','Cmaj7'],'tracks':[{'name':'Melody','notes':[{'pitch':n,'start':i*2,'duration':1.75,'velocity':v} for i,(n,v) in enumerate([(71,78),(69,72),(67,75),(72,82)])]},{'name':'Accompaniment','notes':[{'pitch':n,'start':bar*4,'duration':3.75,'velocity':59} for bar,notes in enumerate([[43,53,59,62],[48,52,55,59]]) for n in notes]}]}
    out.mkdir(parents=True,exist_ok=False);core.dump(out/'composition.json',song);core.write_midi(song,out/'composition.mid');core.dump(out/'validation.json',core.validate(song));core.dump(out/'request.json',{'origin':'deterministic_installation_fixture_not_AI','prompt':'Original installation check'})
    return str(out.resolve())


def execute(a):
    if a.cmd=='doctor':
        result={'workspace':str(core.ORG),'rag_configured':core.RAG is not None,'python':sys.version.split()[0],'platform':sys.platform}
        try:result['ollama_models']=[m['name'] for m in core.api('/api/tags',timeout=5)['models'] if not m.get('remote_host') and not m.get('remote_model') and 'cloud' not in m['name']]
        except OSError as e:result['ollama_error']=str(e)
        return result
    if a.cmd=='rag':return core.retrieve(a.query)
    if a.cmd=='compose':
        run=core.compose(a)
        if a.logic:
            from .logic import open_run
            return open_run(run,a.mcp_config)
        return str(run)
    if a.cmd=='demo':return demo(a.out)
    if a.cmd=='validate':
        song=json.loads(a.file.read_text());return {**core.validate(song),'harmony_warnings':core.harmony_check(song)}
    if a.cmd=='feedback':
        source=a.run/'composition.json';core.validate(json.loads(source.read_text()))
        row={'timestamp':dt.datetime.now().astimezone().isoformat(),'composition_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'rating':a.rating,'note':a.note}
        with (a.run/'feedback.jsonl').open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
        return 'Feedback saved; no weights changed.'
    if a.cmd=='logic':
        from .logic import inspect,open_run
        return inspect(a.mcp_config) if a.action=='inspect' else open_run(a.run,a.mcp_config)
    if a.cmd=='train':
        from . import training as t
        if a.action=='prepare':return str(t.prepare(a.source,a.out))
        if a.action=='smoke-data':return str(t.smoke_data(a.out))
        if a.action=='run':return str(t.train(a.model,a.data,a.out,a.iters))
        if a.action=='generate':return t.generate_with_adapter(a.model,a.adapter,[{'role':'user','content':a.prompt}],a.max_tokens)


def main():
    try:
        result=execute(parser().parse_args());print(json.dumps(result,ensure_ascii=False,indent=2) if isinstance(result,(dict,list)) else result)
    except (ValueError,KeyError,TypeError,OSError,RuntimeError,subprocess.SubprocessError,ImportError) as e:
        print(f'ERROR: {e}',file=sys.stderr);raise SystemExit(1)

if __name__=='__main__':main()
