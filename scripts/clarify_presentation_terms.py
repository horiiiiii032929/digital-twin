"""Add concise specialist-term explanations to the graduate deck."""
from pathlib import Path
import json,copy,subprocess,xml.etree.ElementTree as E
p=Path('reports/generated/slide-build/deck-content.json');data=json.loads(p.read_text())
assert len(data['slides'])==47
s={x['number']:x for x in data['slides']}
def note(n,definition):
 s[n]['termNote']=definition
 s[n]['notes']+='\n\nReading aid: '+definition+'\nOriginal source/scope footer: '+s[n].get('foot','')
# Explain the first mention inside the native diagram rather than adding another tiny note.
f=Path('reports/presentation/diagrams/slides/15-experimental-boundaries.drawio');tree=E.parse(f)
for c in tree.findall('.//mxCell'):
 v=c.get('value','')
 if 'A / B / C / H decision strategies' in v:c.set('value',v.replace('A / B / C / H decision strategies','Alternative decision strategies'))
 if v.startswith('Study E tests learner estimators'):
  c.set('value','Study E tests Bayesian Knowledge Tracing (BKT) and other learner estimators outside the tutoring service. The default adapter uses a delivery proxy.')
new=f.with_name('15-experimental-boundaries-terms.drawio');tree.write(new,encoding='utf-8',xml_declaration=True)
subprocess.run(['/Applications/draw.io.app/Contents/MacOS/draw.io','--export','--format','png','--scale','1.5','--border','8','--embed-diagram','--output',str(new.with_suffix('.png')),str(new)],check=True,stdout=subprocess.DEVNULL)
s[8]['image']=str(new.with_suffix('.png'))
note(8,'BKT (Bayesian Knowledge Tracing) estimates a learner’s concept knowledge from their answers.')
note(13,'p95 latency = the time within which 95% of measured requests finish. Lower means faster responses for most requests.')
note(14,'BM25 (Best Matching 25): keyword ranking. Hybrid combines keyword and semantic retrieval. Qwen3 is a model name.\nCI = confidence interval. Evidence @3 means the required evidence is among the top three retrieved results.')
note(16,'A / B / C are local planner labels defined in the table. V = the added verifier. Lookahead estimates action consequences.')
note(17,'A = deterministic rule baseline. H = guarded replacement: keep A unless a permitted proposal passes the replacement conditions.')
note(18,'CI = confidence interval, showing statistical uncertainty. A = rule baseline; H = guarded replacement. USD = US dollars.')
s[19]['kind']='termComparison'
s[19]['items']=[
 ['Count baseline','Smoothed proportion of correct assessed attempts.'],
 ['BKT · Bayesian Knowledge Tracing','Updates concept knowledge from answers, allowing guesses, mistakes, learning and forgetting.'],
 ['PFA · Performance Factors Analysis','Predicts success from earlier correct and incorrect attempts, giving older evidence less weight in this implementation.']]
s[19]['policies']=[['Constant','Send at each eligible check.'],['Conditional','Send only when progress stalls, or knowledge is low and uncertain.'],['Value-based','Send only when the estimated benefit exceeds the configured threshold.']]
s[19]['takeaway']='The learner model estimates knowledge. The timing policy decides whether to send support.'
s[20]['items'][0][0]='Mean squared error (MSE)'
note(20,'Seed = a reproducible random sequence. Bootstrap resamples learners to estimate uncertainty. Brier is a score name, not an acronym.')
note(21,'BKT = Bayesian Knowledge Tracing. MSE = mean squared error. CI = confidence interval. ↓ means lower is better.\nHere MSE compares hidden-state estimates; Brier scores predictions of the next correct / incorrect answer.')
note(22,'Constant / conditional / value are contact policies. Mastery here is hidden simulator state; it is not a real-student assessment.')
note(23,'Proxy = an indirect substitute. This adapter counts delivered actions rather than demonstrated knowledge. BKT is not integrated here.')
note(34,'BKT = Bayesian Knowledge Tracing. Guess: correct despite not knowing. Slip: incorrect despite knowing. This is a worked calculation.')
note(39,'BKT = Bayesian Knowledge Tracing. PFA = Performance Factors Analysis. MSE = mean squared error (lower is better).\nOracle uses hidden simulator information as a comparison bound. Mastery is the simulator’s day-30 state.')
# Glossary remains optional backup; the first-use reading aids do the main work.
def glossary(title,rows,refs):
 return dict(kind='glossary',title=title,rows=rows,notes='Use this page as a reference when a term needs clarification. The definitions describe the usage in this project.',sources=refs,foot='Reference page. Definitions describe this project’s usage; simulated quantities do not establish real learning.',backup=True)
a=glossary('Reference: learner models and evaluation terms',[
 ['BKT','Bayesian Knowledge Tracing','Probability model of concept knowledge, updated from answers with guessing, slips, learning and forgetting.'],
 ['PFA','Performance Factors Analysis','Predicts success using prior correct / incorrect attempts; this implementation discounts older evidence.'],
 ['MSE','Mean squared error','Average squared difference between an estimate and its target. Here the target is hidden simulator mastery.'],
 ['CI','Confidence interval','Interval expressing sampling uncertainty under the method’s assumptions. It does not account for every source of bias.'],
 ['Brier score','Name of a scoring rule','Mean squared error of a probability prediction against a correct / incorrect outcome. Lower is better.'],
 ['Seed / bootstrap','Simulation / uncertainty methods','A seed reproduces randomness. Bootstrap repeatedly resamples learners or source families for an interval.']],
 s[20]['sources'])
b=glossary('Reference: retrieval and local system labels',[
 ['BM25','Best Matching 25','Keyword-based retrieval ranking using term frequency and document-length adjustment.'],
 ['@3 / p95','Top three / 95th percentile','Evidence @3 checks the top three results. p95 latency is the time at or below which 95% of requests finish.'],
 ['A / B / C','Local planner candidates','A: deterministic rule. B: model proposal. C: proposal plus analytic lookahead.'],
 ['V / H','Verifier / guarded replacement','V accepts or rejects. H falls back to A unless a replacement satisfies the guards.'],
 ['Utility / regret','Synthetic evaluation quantities','Utility is the registered value of the selected action. Regret is its gap from the highest-valued permitted action.'],
 ['Qwen3 / Luna / Terra / Mini','Model names or shortened names','These identify tested models or allocations, not new algorithms or evaluation metrics. Exact models are named in backup slide 40.']],
 s[14]['sources']+s[18]['sources'])
data['slides'] += [a,b]
for i,x in enumerate(data['slides'],1):x['number']=i
p.write_text(json.dumps(data,indent=2))
lines=['# Graduate CS presentation script with term explanations','',f"32 main slides, Questions and 16 backup slides. Main narration remains approximately {data['main_word_count']} words plus the 4:06 video. Reading aids are optional and should not be read twice.",'']
for x in data['slides']:lines += [f"## {x['number']}. {x['title'].replace(chr(10),' ')}",'',x['notes'],'','Sources: '+', '.join(x['sources']),'']
Path('reports/presentation/speaker-script-terms.md').write_text('\n'.join(lines))
print('49 slides. Specialist terms expanded inline and in two backup reference pages.')
