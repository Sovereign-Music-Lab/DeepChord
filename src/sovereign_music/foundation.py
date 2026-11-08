# Copyright 2026 Sovereign Music Lab contributors
# SPDX-License-Identifier: Apache-2.0
"""Original public theory cards and formula-derived chord dictionary. No book I/O."""
from collections import Counter
from importlib.resources import files
import json
import math
from pathlib import Path
import re
import tomllib
import unicodedata

DATA=tomllib.loads(files('sovereign_music').joinpath('assets/foundation.toml').read_text(encoding='utf-8'))
QUALITIES=DATA['qualities']
ROOTS=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B']
LETTERS='CDEFGAB';NATURAL=[0,2,4,5,7,9,11]
ALIASES={'':'maj','M7':'maj7','m(maj7)':'mMaj7','mmaj7':'mMaj7','min':'m','min7':'m7','+':'aug','°':'dim','°7':'dim7','ø':'m7b5','ø7':'m7b5','m6/9':'m6add9'}

def chord(symbol):
    raw=symbol.strip().replace('♭','b').replace('♯','#')
    m=re.fullmatch(r'([A-G])([#b]{0,2})(.*)',raw)
    if not m:raise ValueError('Unsupported chord symbol: '+symbol)
    quality=ALIASES.get(m[3],m[3]).replace('(','').replace(')','')
    if quality not in QUALITIES:raise ValueError('Unsupported chord quality: '+symbol)
    root=(NATURAL[LETTERS.index(m[1])]+m[2].count('#')-m[2].count('b'))%12
    shape=QUALITIES[quality];notes=[]
    for degree,interval in zip(shape['degrees'],shape['intervals']):
        letter=(LETTERS.index(m[1])+degree-1)%7
        diff=((root+interval-NATURAL[letter]+6)%12)-6
        notes.append(LETTERS[letter]+('#'*diff if diff>=0 else 'b'*(-diff)))
    return {'symbol':symbol,'root_pc':root,'quality':quality,'degrees':shape['degrees'],
            'intervals':shape['intervals'],'notes':notes,'pitch_classes':[(root+n)%12 for n in shape['intervals']],
            'origin':'algorithmic_interval_formula','license':DATA['license']}

def records():
    result=[{'id':'theory:'+c['id'],'kind':'theory','title':c['id'],'aliases':c['aliases'],
             'ko':c['ko'],'en':c['en'],'origin':DATA['origin'],'license':DATA['license']} for c in DATA['theory']]
    for root in ROOTS:
        for quality in QUALITIES:
            c=chord(root+quality)
            result.append({'id':'chord:'+root+quality,'kind':'chord','title':root+quality,
                'aliases':[root+quality], 'ko':root+quality+' 구성음: '+' '.join(c['notes']),
                'en':root+quality+' chord tones: '+' '.join(c['notes']),**c})
    return result

def terms(text):
    text=unicodedata.normalize('NFKC',text).lower()
    words=re.findall(r'[a-z0-9#]+|[가-힣]+',text)
    return Counter(words+[word[i:i+2] for word in words if re.search('[가-힣]',word) for i in range(len(word)-1)])

def retrieve(query,top=5):
    if not query.strip():raise ValueError('Query cannot be blank')
    docs=records();q=terms(query);rank=[]
    counters=[terms(' '.join([d['title'],*d.get('aliases',[]),d['ko'],d['en']])) for d in docs]
    df=Counter(t for c in counters for t in c)
    compact=re.sub(r'\s+','',query.lower())
    # Exact chord lookup uses original case to preserve m/M distinctions.
    explicit=set()
    for token in re.findall(r'(?<![A-Za-z])([A-G][#b]?(?:maj7#11|maj9|maj7|mMaj7|m7b5|m13|m11|m9|m7|m6add9|m6|m|dim7|dim|aug|sus4|sus2|7sus4|7b9|7#9|7b5|7#5|9#11|13|11|9|7|6/9|6|5|add9|maj)?)(?![A-Za-z0-9#])',query):
        if len(token)==1 and query.strip()!=token and not re.search(r'(?:chord\s+'+token+r'\b|'+token+r'\s*코드)',query,re.I):continue
        try:
            c=chord(token);explicit.add(ROOTS[c['root_pc']]+c['quality'])
        except ValueError:pass
    for doc,dt in zip(docs,counters):
        score=sum(min(n,dt[t])*math.log(1+len(docs)/(1+df[t])) for t,n in q.items() if t in dt)
        if doc['kind']=='chord':
            score=1000 if doc['title'] in explicit else 0
        else:
            for a in doc['aliases']:
                if len(a)>1 and re.sub(r'\s+','',a.lower()) in compact:score+=30
        if score>0:rank.append({**doc,'retrieval_score':round(score,4)})
    return sorted(rank,key=lambda d:(-d['retrieval_score'],d['id']))[:top]

def context(query,top=5):
    hits=retrieve(query,top)
    lines=['Public foundation: independently authored explanations and computed chord facts; no book text or score transcription.']
    for r in hits:lines += ['['+r['id']+'] '+r['ko']+' / '+r['en']]
    return '\n'.join(lines+([] if hits else ['No matching public foundation evidence.']))

def explain(song,evidence_ids=()):
    from .core import harmony_check
    facts=[]
    for bar,symbol in enumerate(song['chords'],1):
        try:fact=chord(symbol)
        except ValueError:fact={'symbol':symbol,'lookup_status':'unsupported'}
        facts.append({'bar':bar,**fact})
    detected=[]
    for i in range(len(facts)-2):
        a,b,c=facts[i:i+3]
        if all('root_pc' in x for x in [a,b,c]) and (a['root_pc']-c['root_pc'])%12==2 and (b['root_pc']-c['root_pc'])%12==7:
            if a['quality'] in ['m7','m9'] and b['quality'] in ['7','9','13'] and c['quality'] in ['maj','maj7','maj9','6']:
                detected.append({'theory_id':'theory:major251','bars':[i+1,i+2,i+3],'basis':'chord_labels_pattern_not_audition'})
            if a['quality']=='m7b5' and b['quality'] in ['7','7b9','7#9'] and c['quality'] in ['m','m6','m7','m9']:
                detected.append({'theory_id':'theory:minor251','bars':[i+1,i+2,i+3],'basis':'chord_labels_pattern_not_audition'})
    for i,(a,b) in enumerate(zip(facts,facts[1:])):
        if all('root_pc' in c for c in [a,b]) and a['quality'] in ['7','9','13','7b9','7#9'] and (a['root_pc']-b['root_pc'])%12==7:
            detected.append({'theory_id':'theory:guide-tones','bars':[i+1,i+2],
                'basis':'dominant_root_motion_in_chord_labels; individual_voice_resolution_not_proven'})
    return {'chords':facts,'detected_theory_patterns':detected,'retrieved_theory_candidates':list(evidence_ids),
            'harmony_warnings':harmony_check(song),'distinction':'Retrieved concepts are candidates. Detected patterns concern chord labels; no claim of listening or complete harmonic analysis.'}

def write_explanation(song,run,evidence_ids=()):
    from .core import dump
    report=explain(song,evidence_ids);dump(Path(run)/'explanation.json',report)
    lines=['# 사용 코드와 이론 / Chords and theory','', '코드 구성음은 수식 계산, 패턴은 코드명 대조 결과입니다. 검색한 이론과 실제 검출을 구분합니다.','', '| 마디 / Bar | 코드 / Chord | 구성음 / Tones |','|---|---|---|']
    for c in report['chords']:lines.append(f"| {c['bar']} | {c['symbol']} | {' '.join(c.get('notes',[]))} |")
    lines+=['','검출한 패턴 / Detected patterns: '+json.dumps(report['detected_theory_patterns'],ensure_ascii=False),
            '검색한 후보 / Retrieved candidates: '+', '.join(evidence_ids), '',report['distinction']]
    (Path(run)/'EXPLANATION.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return report

def check_review(content):
    """Reject demonstrably wrong structured chord answers; prose stays unverified."""
    try:answer=json.loads(content)
    except (ValueError,TypeError):return {'verified':False,'status':'unstructured_proposal_not_fact_checked'}
    if not isinstance(answer,dict) or 'symbol' not in answer:return {'verified':False,'status':'no_supported_structured_fact'}
    try:expected=chord(answer['symbol'])
    except (ValueError,TypeError):return {'verified':False,'status':'unsupported_chord'}
    fields=[k for k in ['notes','pitch_classes','intervals'] if k in answer]
    errors=[k for k in fields if answer[k]!=expected[k]]
    return {'verified':bool(fields) and not errors,'status':'formula_mismatch' if errors else 'checked_fields_only',
            'checked_fields':fields,'mismatched_fields':errors,'computed_chord':expected,
            'scope':'Only supplied structured chord fields, not prose or musical quality.'}

def export(out):
    """Reproducible public RAG records and separately grouped LoRA examples."""
    from .core import dump
    out=Path(out);out.mkdir(parents=True,exist_ok=False);docs=records();rows=[]
    for doc in docs:
        for lang in ['ko','en']:
            answer=(doc[lang] if doc['kind']=='theory' else json.dumps({k:doc[k] for k in ['symbol','notes','pitch_classes','intervals']},ensure_ascii=False))
            prompt=(f"Explain {doc['title']} ({lang})." if doc['kind']=='theory' else f"Return chord tones for {doc['symbol']} as JSON ({lang}).")
            rows.append({'reviewed':True,'review_basis':'authored_theory_or_formula_checked_not_listening',
                'task':'theory_qa' if doc['kind']=='theory' else 'chord_lookup','foundation_id':doc['id'],
                'group_id':doc['id'] if doc['kind']=='theory' else 'chord-family:'+doc['quality'],
                'messages':[{'role':'user','content':prompt},{'role':'assistant','content':answer}]})
    for filename,data in [('rag.jsonl',docs),('reviewed.jsonl',rows)]:
        (out/filename).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in data),encoding='utf-8',newline='\n')
    import hashlib
    dump(out/'manifest.json',{'foundation_version':DATA['version'],'origin':DATA['origin'],'license':DATA['license'],
        'theory_cards':len(DATA['theory']),'chord_formulas':len(QUALITIES),'chord_entries':len(ROOTS)*len(QUALITIES),
        'rag_records':len(docs),'training_records':len(rows),'files_sha256':{n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ['rag.jsonl','reviewed.jsonl']},
        'evaluation_limit':'Synthetic factual exercises; not a musical creativity or generalization benchmark.'})
    return out
