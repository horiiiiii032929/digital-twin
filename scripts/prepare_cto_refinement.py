"""Prepare a visual refinement of the approved 31-slide narrative."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
build=root/'reports/generated/cto-refined-build';build.mkdir(parents=True,exist_ok=True)
d=json.loads((root/'reports/generated/cto-slide-build/deck-content.json').read_text())
for s in d['slides']:
    if s.get('image','').startswith('reports/presentation/diagrams/cto/'):
        s['image']=s['image'].replace('/cto/','/cto-refined/')
    s['visual_review']='Question → evidence or mechanism → decision; preserve source-linked limitations.'
changes={2:'agenda',6:'requirements',11:'completeness',18:'utility',19:'proxy',20:'models',27:'trial',30:'experiment',31:'development'}
for n,k in changes.items(): d['slides'][n-1]['kind']=k
s=d['slides'][13];s['kind']='charts';s['charts']=[
{'title':'Complete, supported answers (%)','categories':['BM25','Hybrid','Required'],'series':[{'name':'Rate','values':[63.25,62,95],'fill':'#285E8E','points':[{'idx':2,'fill':'#A6AFBA'}]}],'max':100,'format':'0.00','axisFormat':'0','detail':'800 answerable cases. Both miss 95%.'},
{'title':'Correct refusal / clarification (%)','categories':['BM25','Hybrid','Required'],'series':[{'name':'Rate','values':[96,95,98],'fill':'#285E8E','points':[{'idx':2,'fill':'#A6AFBA'}]}],'max':100,'format':'0.00','axisFormat':'0','detail':'200 boundary cases. Both miss 98%.'}]
s['foot']='BM25: keyword ranking. Hybrid: keyword + semantic retrieval. Gray bars show required thresholds.\nBoth paths share the answer check; grounded answers must be complete and source-supported.';s['limit']=''
s=d['slides'][23];s['kind']='charts';s['charts']=[{'title':'Goal completions in 72 matched histories per version','categories':['Old rule','Target-scoped rule'],'series':[{'name':'Supported','values':[14,15],'fill':'#285E8E'},{'name':'Unsupported','values':[12,0],'fill':'#B56A43'}],'max':30,'format':'0','stacked':True}];s['side']=[['12 → 0 false completions','Correct cache-coherence answers no longer complete an unassessed virtual-memory goal.'],['Retain the correction','Evidence must match the goal’s concepts, as well as its student and course release.']];s['foot']='Same 72 synthetic histories per version. Autonomous slice: 56 extra messages; mastery change −0.0024.\nThe correction improves state validity; it does not establish a learning gain.';s['limit']=''
s=d['slides'][12];s['side']=[['+102 complete answers','253 → 355 of the same 397 cases. The check now names the required facts and count.'],['0 gain from extra ranking','355 answers with or without ranking. p95 latency rises from 1.36 to 2.79 ms.']]
s=d['slides'][21];s['charts'][0]['detail']='Conditional: 7 fewer messages than constant.';s['charts'][1]['detail']='Conditional: 0.012 lower mean mastery.'
# Keep symbols defined on first use and match the displayed chart categories.
s=d['slides'][20];s['foot']='BKT = Bayesian Knowledge Tracing; PFA = Performance Factors Analysis; CI = confidence interval.\nMSE compares estimated with hidden knowledge; Brier compares predicted answer probability with the observed outcome.'
(build/'deck-content.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
