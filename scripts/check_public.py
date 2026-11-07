#!/usr/bin/env python3
"""Audit the Git index, not ignored working files. Intended before every commit/release."""
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
TOP={'.gitignore','.gitattributes','README.md','LICENSE','pyproject.toml','Start.command','AGENTS.md','MANIFEST.in'}
DIRS={'src','tests','scripts','docs','.github'}
EXT={'.py','.md','.toml','.txt','.yml','.yaml','.command'}

def issue(name,data,mode='100644'):
    p=Path(name)
    if mode=='120000':return 'symlink is not distributable'
    if p.parts[0] not in DIRS and name not in TOP:return 'unapproved path'
    if name not in TOP and p.suffix.lower() not in EXT:return 'unapproved file type'
    if any(x in name.lower() for x in ['.egg-info','__pycache__','rag-evidence','adapter_config']):return 'runtime/generated file'
    if len(data)>250000:return 'oversized source file'
    try:text=data.decode('utf-8')
    except UnicodeDecodeError:return 'binary payload'
    if '\x00' in text:return 'binary content'
    patterns=[r'/Users/' + r'[^/\s]+/',r'-----BEGIN '+r'(?:RSA |OPENSSH |EC )?PRIVATE KEY-----',r'(?:ghp_|github_pat_|hf_)'+r'[A-Za-z0-9_]{25,}']
    if any(re.search(x,text) for x in patterns):return 'private path or credential pattern'
    return None


def main():
    entries=subprocess.check_output(['git','ls-files','--stage','-z'],cwd=ROOT).decode().split('\0')
    count=0;errors=[]
    for entry in filter(None,entries):
        meta,name=entry.split('\t',1);mode,oid,stage=meta.split()
        data=subprocess.check_output(['git','cat-file','blob',oid],cwd=ROOT)
        problem=issue(name,data,mode);count+=1
        if problem:errors.append(f'{name}: {problem}')
    if not count:errors.append('No staged/tracked files to audit')
    if errors:print('\n'.join(errors),file=sys.stderr);return 1
    print(f'Public index audit passed: {count} text source/documentation files; no datasets or weights.');return 0

if __name__=='__main__':raise SystemExit(main())
