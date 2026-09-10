"""Export standard UML activity/component figures for the presentation."""
from pathlib import Path
import subprocess
import xml.etree.ElementTree as E
from scripts.build_standard_sdlc_diagrams import Diagram, INK, LIGHT

OUT=Path('reports/presentation/diagrams/failures');OUT.mkdir(parents=True,exist_ok=True)
pages=[]
def begin(name,title,scope):
 d=Diagram(name,title,scope);pages.append(d);return d
def initial(d,x,y): return d.node(x,y,26,26,'','ellipse;fillColor='+INK+';')
def end(d,x,y): return d.node(x,y,30,30,'','shape=endState;fillColor='+INK+';')
def act(d,x,y,w,h,text): return d.node(x,y,w,h,text,'rounded=1;arcSize=14;',29)
def diamond(d,x,y,text):return d.node(x,y,150,110,text,'rhombus;',23)

d=begin('09-factual-designs','UML Activity: factual paths tried','Historical Round 1. All paths receive the same question and course evidence.')
for i,(name,steps) in enumerate([
 ('Lexical control',['Retrieve lexical matches','Accept any evidence hit','Extract a source response']),
 ('Evidence-first',['Retrieve hierarchical evidence','Require whole-question coverage','Answer or abstain']),
 ('Plan-observe',['Decompose and retrieve','Combine retrieval observations','Require whole-question coverage','Answer or abstain'])]):
 x=65+i*510;d.text(x,170,470,45,name,30,True);initial(d,x+220,235)
 for j,t in enumerate(steps):
  y=300+j*135;act(d,x+10,y,430,85,t)
  d.line((x+233,261 if j==0 else y-50),(x+233,y))
 end(d,x+219,300+len(steps)*135);d.line((x+233,250+len(steps)*135),(x+233,300+len(steps)*135))
d.foot('Coverage was an action-selection defect: question scaffolding became required evidence. This does not reject event sourcing generally.')

d=begin('10-reject-only','UML Activity: reject-only verification','Historical C+V path. A rejected selection does not obtain a replacement action.')
initial(d,65,370);act(d,140,335,310,110,'C selects a\npermitted action');diamond(d,565,335,'Verifier\naccepts?');act(d,875,230,410,100,'Execute the selected action');act(d,875,575,410,100,'Return no action');end(d,1410,375)
d.line((91,383),(140,383));d.line((450,390),(565,390));d.line((715,390),(875,280),'[accept]',points=[(790,390),(790,280)]);d.line((640,445),(875,625),'[reject]',points=[(640,625)]);d.line((1285,280),(1425,375),points=[(1425,280)]);d.line((1285,625),(1425,405),points=[(1425,625)])
d.note(140,720,1150,125,'Failure mechanism: the extra verifier can remove a usable move without supplying a better one. Rejection and action validity require separate evaluation.',28)

d=begin('11-guarded-replacement','UML Activity: guarded replacement','H preserves deterministic A unless an authorized proposal passes the replacement guards.')
initial(d,60,310);diamond(d,145,268,'Authorized\nevidence?');act(d,390,270,300,105,'Compute baseline A');act(d,785,270,305,105,'Evaluate proposal\nand analytic value');diamond(d,1190,260,'Replacement\nguards pass?')
act(d,140,620,300,100,'No action');act(d,785,620,305,100,'Keep baseline A');act(d,1190,620,320,100,'Use proposal')
d.line((86,323),(145,323));d.line((295,323),(390,323),'[yes]');d.line((220,378),(290,620),'[no]',points=[(220,535),(290,535)]);d.line((690,323),(785,323));d.line((1090,323),(1190,323));d.line((1265,370),(1350,620),'[yes]',points=[(1350,450)]);d.line((1190,315),(940,620),'[no]',points=[(1140,315),(1140,520),(940,520)])
d.note(400,790,1100,105,'Replacement requires a permitted, valid proposal that agrees with the analytic best action and improves value by at least 0.04.',28)

# Each disconnected column is an explicitly distinct activity with its own start/end.
d=begin('12-delivery-proxy','UML Activity: the default planner input','Current adapter constructs a delivery proxy. Assessment and completion follow a separate path.')
initial(d,145,200);act(d,65,275,420,100,'Read delivered goal actions');act(d,65,445,420,100,'Count deliveries as n');act(d,65,625,420,130,'Set probability proxy\n(n + 1) / (n + 2)');end(d,260,830)
d.line((158,226),(275,275),points=[(158,250),(275,250)]);d.line((275,375),(275,445));d.line((275,545),(275,625));d.line((275,755),(275,830))
d.note(640,275,850,190,'No student-answer step is required on this path.\n0 deliveries gives 0.50.\n1 delivery gives 0.67.',32)
d.note(640,545,850,200,'Committed concept assessments separately inform completion. The experimental BKT estimator is not integrated into this default adapter.',30)

d=begin('13-completion-scope','UML Activity: goal-completion evidence scope','Historical guard and corrected guard. These are separate activities, not one sequential execution.')
for x,title,steps in [(65,'Historical',['Read broad learner evidence','Apply completion thresholds','Complete the active objective']), (840,'Corrected',['Resolve exact objective concepts','Read committed target evidence','Require all targets to pass','Complete that objective only'])]:
 d.text(x,170,650,45,title,32,True);initial(d,x+290,230)
 for i,t in enumerate(steps):
  y=295+i*125;act(d,x,y,620,80,t)
  d.line((x+303,256 if i==0 else y-45),(x+303,y))
 end(d,x+288,295+len(steps)*125);d.line((x+303,250+len(steps)*125),(x+303,295+len(steps)*125))
d.foot('The corrected completion check uses two correct assessments per target, no incorrect assessment, and confidence at least 0.5. It is not mastery validation.')

d=begin('14-operational-components','UML Component: operational dialogue simulation','Study G only. Synthetic student text and elapsed time enter actual product services.')
for x,y,w,h,t in [(65,260,380,150,'«component»\nSynthetic student driver'),(65,650,380,150,'«component»\nVirtual clock / scheduler'),(650,260,470,200,'«component»\nTutoring and autonomy\nservices under test'),(650,650,470,150,'«component»\nPersisted conversations,\ngoals and delivery records'),(1240,270,310,170,'«component»\nConfigured model\nprovider'),(1240,650,310,150,'«component»\nOperating checks')]:d.node(x,y,w,h,t,'shape=component;',27)
d.line((445,335),(650,335),'student input','dashed=1;');d.line((445,715),(650,420),'due work','dashed=1;',points=[(530,715),(530,420)]);d.line((885,460),(885,650),'reads / writes','dashed=1;');d.line((1120,335),(1240,335),'inference','dashed=1;');d.line((1240,725),(1120,725),'inspects','dashed=1;')
d.foot('Student attendance and replies are simulated. This operating trial does not measure hidden mastery. Study E uses a separate learner/timing simulator.')

root=E.Element('mxfile',host='app.diagrams.net',version='30.0.4')
for d in pages:d.bind();root.append(d.d)
E.indent(root);source=OUT/'failed-designs.drawio';E.ElementTree(root).write(source,encoding='utf-8',xml_declaration=True)
for i,d in enumerate(pages,1):
 subprocess.run(['/Applications/draw.io.app/Contents/MacOS/draw.io','--export','--page-index',str(i),'--format','png','--scale','1.5','--embed-diagram','--output',str(OUT/(d.name+'.png')),str(source)],check=True,stdout=subprocess.DEVNULL)
print(source)
