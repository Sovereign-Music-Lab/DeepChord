#!/usr/bin/env python3
# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Audit the Git index, not ignored working files. Intended before every commit/release."""
from pathlib import Path
import hashlib
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
TOP={'.gitignore','.gitattributes','README.md','README.ko.md','LICENSE','NOTICE','pyproject.toml','Start.command','AGENTS.md','MANIFEST.in'}
DIRS={'src','tests','scripts','docs','.github','site'}
EXT={'.py','.md','.toml','.txt','.yml','.yaml','.command','.html','.css','.js','.svg','.xml'}
TEXT_SPECIAL={'site/.nojekyll','site/LICENSE','site/NOTICE'}
# Exact, visually reviewed public brand assets. No general binary-file exception.
PUBLIC_ASSETS={
    'site/assets/apple-touch-icon.png':'34ce539c7c4504d86763a910b963086c586d1c5b53ad352ae0a3e4b7fb60cff0',
    'site/assets/favicon-32.png':'d598327e44cef9a8c32a00fb57acf6c53fead1bf0fac03054b83f6185673830e',
    'site/assets/og-en.png':'77ca39f85fcf3c8e97d32fbb3fd369ec5ffd3cd0315ce044ebb8d3a4acb8cb74',
    'site/assets/og-ko.png':'830063551f4efb40c1349d78be7de3fd0bf7b69c21b959544117f96aeafaced2',
    'site/favicon.ico':'f65790f27d79e32dfae7b5c58d2b5bbc21f245166dcbe5f47b24df47af8ee354',
}

def issue(name,data,mode='100644'):
    p=Path(name)
    if mode=='120000':return 'symlink is not distributable'
    if name in PUBLIC_ASSETS:
        if hashlib.sha256(data).hexdigest()!=PUBLIC_ASSETS[name]:return 'brand image differs from reviewed content'
        return None
    if p.parts[0] not in DIRS and name not in TOP:return 'unapproved path'
    if name not in TOP and name not in TEXT_SPECIAL and p.suffix.lower() not in EXT:return 'unapproved file type'
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
    print(f'Public index audit passed: {count} reviewed source/documentation/brand files; no datasets or weights.');return 0

if __name__=='__main__':raise SystemExit(main())
