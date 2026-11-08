# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Optional offline Transformers/PEFT backend for Windows, Linux and macOS.

Requires a compatible local Hugging Face model, not an MLX/Ollama quantized tag.
"""
import hashlib,json,os
from pathlib import Path
from .core import dump

def train(model,data,out,iters):
    from .training import local_path,offline_env
    model=local_path(model);data=Path(data).resolve();out=Path(out).resolve()
    config=json.loads((model/'config.json').read_text(encoding='utf-8'))
    if config.get('quantization') or config.get('quantization_config'):
        raise ValueError('Portable training currently requires unquantized HF safetensors; no automatic MLX/GGUF/NVFP4 conversion.')
    if not 1<=iters<=100000:raise ValueError('iters must be 1..100000')
    manifest=json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    for split in ['train','valid','test']:
        if manifest['counts'][split]<1 or hashlib.sha256((data/f'{split}.jsonl').read_bytes()).hexdigest()!=manifest['split_sha256'][split]:raise ValueError('Dataset changed; review and prepare again')
    os.environ.update({k:v for k,v in offline_env().items() if k.startswith(('HF_','TRANSFORMERS_','WANDB_'))})
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer,Trainer,TrainingArguments,DataCollatorForSeq2Seq
    from peft import LoraConfig,get_peft_model
    tokenizer=AutoTokenizer.from_pretrained(str(model),local_files_only=True,trust_remote_code=False)
    if tokenizer.pad_token_id is None:tokenizer.pad_token=tokenizer.eos_token
    def load(split):
        rows=[]
        for line in (data/f'{split}.jsonl').read_text(encoding='utf-8').splitlines():
            messages=json.loads(line)['messages']
            ids=tokenizer.apply_chat_template(messages,tokenize=True)
            prompt=tokenizer.apply_chat_template(messages[:-1],tokenize=True,add_generation_prompt=True)
            if hasattr(ids,'keys'):ids=ids['input_ids']
            if hasattr(prompt,'keys'):prompt=prompt['input_ids']
            if len(ids)>2048:raise ValueError('Example exceeds 2048 tokens')
            if ids[:len(prompt)]!=prompt or len(ids)<=len(prompt):raise ValueError('Chat template cannot reliably mask this prompt; use a compatible template')
            rows.append({'input_ids':ids,'attention_mask':[1]*len(ids),'labels':[-100]*len(prompt)+ids[len(prompt):]})
        return rows
    splits={s:load(s) for s in ['train','valid','test']}
    base=AutoModelForCausalLM.from_pretrained(str(model),local_files_only=True,trust_remote_code=False,torch_dtype=torch.float32)
    if not all(any(n.endswith(k) for n,_ in base.named_modules()) for k in ['q_proj','v_proj']):raise ValueError('Model requires an explicitly supported LoRA target mapping (q_proj/v_proj)')
    tuned=get_peft_model(base,LoraConfig(r=8,lora_alpha=16,lora_dropout=0.05,target_modules=['q_proj','v_proj'],task_type='CAUSAL_LM'))
    out.mkdir(parents=True,exist_ok=False)
    provenance={'backend':'transformers','status':'running','model_path':str(model),'model_config_sha256':hashlib.sha256((model/'config.json').read_bytes()).hexdigest(),'data_manifest':manifest,'iters':iters}
    dump(out/'run.json',provenance)
    try:
        args=TrainingArguments(output_dir=str(out/'checkpoints'),max_steps=iters,per_device_train_batch_size=1,per_device_eval_batch_size=1,learning_rate=1e-4,save_strategy='no',logging_steps=1,report_to=[],seed=42,dataloader_num_workers=0,use_cpu=not torch.cuda.is_available())
        trainer=Trainer(model=tuned,args=args,train_dataset=splits['train'],eval_dataset=splits['valid'],data_collator=DataCollatorForSeq2Seq(tokenizer,padding=True,label_pad_token_id=-100))
        trainer.train();tuned.save_pretrained(str(out));tokenizer.save_pretrained(str(out))
        provenance.update(status='trained',validation_metrics=trainer.evaluate(),test_metrics=trainer.evaluate(splits['test']),evaluation_returncode=0)
    except BaseException:
        provenance['status']='failed';dump(out/'run.json',provenance);raise
    dump(out/'run.json',provenance);return out

def generate(model,adapter,messages,max_tokens):
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from peft import PeftModel
    tokenizer=AutoTokenizer.from_pretrained(str(model),local_files_only=True,trust_remote_code=False)
    base=AutoModelForCausalLM.from_pretrained(str(model),local_files_only=True,trust_remote_code=False,torch_dtype=torch.float32)
    tuned=PeftModel.from_pretrained(base,str(adapter),local_files_only=True);tuned.eval()
    ids=tokenizer.apply_chat_template(messages,add_generation_prompt=True,return_tensors='pt')
    if hasattr(ids,'keys'):ids=ids['input_ids']
    with torch.no_grad():response=tuned.generate(input_ids=ids,max_new_tokens=max_tokens,do_sample=False,pad_token_id=tokenizer.eos_token_id)
    content=tokenizer.decode(response[0,ids.shape[1]:],skip_special_tokens=True)
    return {'message':{'role':'assistant','content':content},'backend':'transformers-local-adapter'}
