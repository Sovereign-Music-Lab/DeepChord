# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Offline MLX LoRA workflow. Private data and weights are never distributed."""
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from .core import validate, harmony_check, dump


def local_path(value):
    path=Path(value).expanduser().resolve()
    if not path.is_dir() or not (path/'config.json').is_file():
        raise ValueError('Use a local MLX model directory containing config.json; Ollama tags are not MLX training paths.')
    if not list(path.glob('*.safetensors')):
        raise ValueError('No local model weights found')
    return path


def records(path):
    rows=[]
    for line in Path(path).read_text().splitlines():
        if not line.strip(): continue
        row=json.loads(line)
        if row.get('reviewed') is not True or not row.get('group_id'):
            raise ValueError('Each record needs reviewed:true and a group_id identifying the original composition family')
        messages=row['messages']
        if [m['role'] for m in messages]!=['user','assistant'] or not all(isinstance(m['content'],str) and m['content'] for m in messages):
            raise ValueError('Expected nonempty user/assistant messages')
        song=json.loads(messages[1]['content']);validate(song)
        issues=harmony_check(song)
        if issues: raise ValueError('Fix harmony before training: '+str(issues))
        rows.append(row)
    return rows


def prepare(source,out):
    rows=records(source); groups=sorted({str(r['group_id']) for r in rows})
    if len(groups)<3:raise ValueError('At least three distinct composition groups are required for train/valid/test separation')
    random.Random(42).shuffle(groups)
    n=max(1,len(groups)//5)
    assignment={g:('test' if i<n else 'valid' if i<2*n else 'train') for i,g in enumerate(groups)}
    parts={k:[] for k in ['train','valid','test']}; seen={}
    for r in rows:
        # Canonicalize assistant JSON so whitespace cannot hide duplicates across splits.
        key=hashlib.sha256(json.dumps(json.loads(r['messages'][1]['content']),sort_keys=True).encode()).hexdigest()
        split=assignment[str(r['group_id'])]
        if key in seen:
            if seen[key]!=split:raise ValueError('Duplicate composition crosses data splits')
            continue
        seen[key]=split;parts[split].append({'messages':r['messages']})
    if not all(parts.values()):raise ValueError('Empty split after deduplication')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for split,items in parts.items():
        (out/f'{split}.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in items))
    dump(out/'manifest.json',{'source_sha256':hashlib.sha256(Path(source).read_bytes()).hexdigest(),'split_sha256':{k:hashlib.sha256((out/f'{k}.jsonl').read_bytes()).hexdigest() for k in parts},'seed':42,'group_split':assignment,'counts':{k:len(v) for k,v in parts.items()},'meaning':'Reviewed symbolic examples; no claim of musical-quality evaluation'})
    return out


def offline_env():
    return {**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','WANDB_DISABLED':'true'}


def train(model,data,out,iters=100):
    model=local_path(model);data=Path(data).resolve();out=Path(out).resolve()
    if not 1<=iters<=100000:raise ValueError('iters must be 1..100000')
    for split in ['train','valid','test']:
        if not (data/f'{split}.jsonl').is_file():raise ValueError('Run dataset preparation first')
    # Validate once more; do not accept arbitrary unreviewed remote datasets.
    manifest=json.loads((data/'manifest.json').read_text())
    for split in ['train','valid','test']:
        if manifest['counts'][split]<1:raise ValueError('Empty split')
        expected=manifest.get('split_sha256',{}).get(split)
        if expected!=hashlib.sha256((data/f'{split}.jsonl').read_bytes()).hexdigest():
            raise ValueError('Dataset changed after preparation; review and prepare again')
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(str(model),local_files_only=True,trust_remote_code=False)
    for split in ['train','valid','test']:
        for line in (data/f'{split}.jsonl').read_text().splitlines():
            tokens=tokenizer.apply_chat_template(json.loads(line)['messages'],tokenize=True)
            if hasattr(tokens,'keys'):tokens=tokens['input_ids']
            if len(tokens)>2048:raise ValueError('Example exceeds 2048 tokens; shorten it before training (no silent truncation)')
    out.mkdir(parents=True,exist_ok=False)
    command=[sys.executable,'-m','mlx_lm','lora','--model',str(model),'--train','--data',str(data),'--adapter-path',str(out),'--iters',str(iters),'--batch-size','1','--num-layers','2','--learning-rate','0.0001','--max-seq-length','2048','--mask-prompt','--grad-checkpoint','--steps-per-report','1','--steps-per-eval',str(max(1,iters)),'--val-batches','1','--save-every',str(iters),'--seed','42']
    provenance={'model_path':str(model),'model_config_sha256':hashlib.sha256((model/'config.json').read_bytes()).hexdigest(),'data_manifest':manifest,'command':command,'status':'running'}
    dump(out/'run.json',provenance)
    with (out/'train.log').open('w') as log:
        process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=offline_env())
    adapter=out/'adapters.safetensors'
    provenance['status']='trained' if process.returncode==0 and adapter.is_file() else 'failed'
    provenance['returncode']=process.returncode
    if adapter.is_file():provenance['adapter_sha256']=hashlib.sha256(adapter.read_bytes()).hexdigest()
    dump(out/'run.json',provenance)
    if provenance['status']!='trained':raise RuntimeError(f'Training failed; see {out}/train.log')
    evaluation=[sys.executable,'-m','mlx_lm','lora','--model',str(model),'--data',str(data),'--adapter-path',str(out),'--test','--test-batches','-1','--batch-size','1','--max-seq-length','2048']
    with (out/'test.log').open('w') as log:
        result=subprocess.run(evaluation,stdout=log,stderr=subprocess.STDOUT,env=offline_env())
    provenance['evaluation_returncode']=result.returncode;dump(out/'run.json',provenance)
    if result.returncode:raise RuntimeError(f'Trained, but held-out evaluation failed: {out}/test.log')
    return out


def generate_with_adapter(model,adapter,messages,max_tokens=6500):
    model=local_path(model);adapter=Path(adapter).resolve()
    run=json.loads((adapter/'run.json').read_text())
    if run['status']!='trained' or Path(run['model_path']).resolve()!=model:
        raise ValueError('Adapter/base model mismatch or incomplete training')
    # No remote model IDs and no remote-code execution.
    os.environ.update({k:v for k,v in offline_env().items() if k.startswith(('HF_','TRANSFORMERS_'))})
    from mlx_lm import load,generate
    m,t=load(str(model),adapter_path=str(adapter),tokenizer_config={'trust_remote_code':False})
    prompt=t.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
    text=generate(m,t,prompt=prompt,max_tokens=max_tokens,verbose=False)
    return {'message':{'role':'assistant','content':text},'backend':'mlx-local-adapter'}


def smoke_data(path):
    """New algorithmic one-bar exercises, for pipeline testing only."""
    rows=[]
    for i in range(12):
        root=i;label=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'][i]+'maj7'
        notes=[{'pitch':48+root+n,'start':0,'duration':3.8,'velocity':60} for n in [0,4,7,11]]
        song={'title':f'Synthetic test {i}','tempo':72+i,'bars':1,'chords':[label],'tracks':[{'name':'Accompaniment','notes':notes}]}
        rows.append({'reviewed':True,'group_id':f'smoke-{i}','messages':[{'role':'user','content':f'Return a one-bar {label} piano chord as JSON.'},{'role':'assistant','content':json.dumps(song)}]})
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:
        f.write(''.join(json.dumps(r)+'\n' for r in rows))
    return path
