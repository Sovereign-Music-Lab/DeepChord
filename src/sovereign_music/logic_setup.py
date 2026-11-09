# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Build the pinned optional MCP extension in a new, isolated directory."""
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import subprocess
import sys
import tomllib


def install(destination, *, source_repository=None, build_configuration='release'):
    """Download code, apply the reviewed patch, build, and write a private config.

    Existing installations and macOS permissions are never modified. The
    optional local repository is only a Git object source for offline tests;
    the pinned revision and bundled patch still determine every source change.
    """
    if sys.platform != 'darwin':
        raise ValueError('The Logic extension requires macOS and Xcode command line tools')
    if build_configuration not in ('debug','release'):
        raise ValueError('Unknown build configuration')
    destination = Path(destination).expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('Choose a new folder; an existing MCP installation is never overwritten')
    assets = files('sovereign_music').joinpath('assets')
    metadata = tomllib.loads(assets.joinpath('logic-extension.toml').read_text())
    patch = assets.joinpath('logic-region-edit.patch.txt').read_bytes()
    if hashlib.sha256(patch).hexdigest() != metadata['patch_sha256']:
        raise ValueError('Bundled MCP extension checksum mismatch')
    destination.mkdir(parents=True)
    checkout = destination/'source'
    status = {'status':'building',**metadata,'configuration':build_configuration}
    report = destination/'installation.json'
    def checkpoint(): report.write_text(json.dumps(status,indent=2)+'\n')
    checkpoint()
    log_path = destination/'build.log'
    print(f'Building the Logic extension. This can take several minutes. Progress log: {log_path}', file=sys.stderr, flush=True)
    try:
        with log_path.open('w') as log:
            def run(args, *, cwd=destination, input=None):
                return subprocess.run(args,cwd=cwd,input=input,stdout=log,stderr=subprocess.STDOUT,check=True)
            run(['git','init',str(checkout)])
            run(['git','remote','add','origin',str(source_repository or metadata['upstream'])],cwd=checkout)
            run(['git','fetch','--depth','1','origin',metadata['revision']],cwd=checkout)
            run(['git','checkout','--detach','FETCH_HEAD'],cwd=checkout)
            revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=checkout,text=True).strip()
            if revision != metadata['revision']: raise RuntimeError('Fetched MCP revision mismatch')
            run(['git','apply','--check','-'],cwd=checkout,input=patch)
            run(['git','apply','-'],cwd=checkout,input=patch)
            run(['swift','build','-c',build_configuration,'-j','4','--product','LogicProMCP'],cwd=checkout)
            bin_path = subprocess.check_output(['swift','build','-c',build_configuration,'--show-bin-path'],cwd=checkout,text=True).strip()
        binary = Path(bin_path)/'LogicProMCP'
        if not binary.is_file(): raise RuntimeError('Built MCP executable was not found')
        config = destination/'logic.toml'
        config.write_text('[logic]\ncommand = '+json.dumps(str(binary))+'\nargs = []\n\n[logic.env]\nLOGIC_PRO_BUNDLE_ID = "com.apple.logic10"\n')
        status.update(status='built',binary=str(binary),config=str(config),
                      binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                      accessibility_permission_verified=False,live_edit_verified=False)
        checkpoint()
    except BaseException as error:
        status.update(status='failed',error=str(error)); checkpoint()
        raise RuntimeError(f'MCP build failed. Details: {log_path}') from error
    return status
