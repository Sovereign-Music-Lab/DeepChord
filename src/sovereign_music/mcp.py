# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Bounded stdio MCP client; no arbitrary model-selected tool execution."""
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import tomllib
from . import __version__


class ToolError(RuntimeError):
    """Keep full tool evidence without flooding the musician's terminal."""
    def __init__(self, name, command, response):
        self.response = response
        detail = response.get('structuredContent', {})
        if not isinstance(detail, dict): detail = {}
        reason = next((detail[k] for k in ('reason','error','message','hint')
                       if isinstance(detail.get(k),str) and detail[k].strip()), 'tool reported failure')
        super().__init__(f'{name}.{command}: {reason[:240]}')

class Client:
    def __init__(self,config):
        data=tomllib.loads(Path(config).expanduser().read_text(encoding='utf-8'))
        entry=data.get('mcp_servers',{}).get('logic-pro',data.get('logic'))
        if not entry or not entry.get('command'):raise ValueError('Configure [logic] command/args/env or an existing [mcp_servers.logic-pro] entry')
        self.p=subprocess.Popen([entry['command'],*entry.get('args',[])],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding="utf-8",bufsize=1,env={**os.environ,**entry.get('env',{})})
        self.q=queue.Queue();self.seq=0
        threading.Thread(target=self._read,daemon=True).start()
        try:
            self.server=self.request('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'deepchord','version':__version__}})
            if self.server.get('protocolVersion') not in ('2024-11-05','2025-03-26','2025-06-18'):raise RuntimeError('Unsupported MCP protocol')
            self.send({'method':'notifications/initialized'})
        except BaseException:self.close();raise
    def _read(self):
        try:
            for line in self.p.stdout:
                try:self.q.put(json.loads(line))
                except json.JSONDecodeError:pass
        finally:self.q.put(None)
    def send(self,value):
        self.p.stdin.write(json.dumps({'jsonrpc':'2.0',**value})+'\n');self.p.stdin.flush()
    def request(self,method,params,timeout=45):
        self.seq+=1;i=self.seq;self.send({'id':i,'method':method,'params':params});deadline=time.monotonic()+timeout
        while True:
            try:r=self.q.get(timeout=max(.001,deadline-time.monotonic()))
            except queue.Empty:
                self.send({'method':'notifications/cancelled','params':{'requestId':i,'reason':'timeout'}})
                raise TimeoutError('MCP timeout; operation outcome unknown. Do not automatically retry writes.')
            if r is None:raise RuntimeError('MCP process closed')
            if r.get('id')==i and 'method' not in r:
                if 'error' in r:raise RuntimeError(r['error'])
                return r.get('result',{})
            if 'id' in r and 'method' in r:self.send({'id':r['id'],'error':{'code':-32601,'message':'Not supported'}})
    def tool(self,name,command,params=None,*,timeout=90):
        result=self.request('tools/call',{'name':name,'arguments':{'command':command,'params':params or {}}},timeout=timeout)
        if result.get('isError'):raise ToolError(name,command,result)
        return result
    def close(self):
        if self.p.stdin and not self.p.stdin.closed:self.p.stdin.close()
        try:self.p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.p.terminate()
            try:self.p.wait(timeout=3)
            except subprocess.TimeoutExpired:self.p.kill();self.p.wait()
        self.p.stdout.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
