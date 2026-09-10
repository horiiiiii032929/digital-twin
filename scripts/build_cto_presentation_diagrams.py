"""Build focused draw.io C4, ER and UML diagrams for the CTO presentation."""
from pathlib import Path
import xml.etree.ElementTree as E
import subprocess
import sys
OUT=Path('reports/presentation/diagrams/cto');OUT.mkdir(parents=True,exist_ok=True)
class D:
 def __init__(self,name,w=1500,h=530):
  self.name=name;self.root=E.Element('mxfile',host='app.diagrams.net');page=E.SubElement(self.root,'diagram',name=name,id=name)
  model=E.SubElement(page,'mxGraphModel',page='1',pageWidth=str(w),pageHeight=str(h));self.r=E.SubElement(model,'root');E.SubElement(self.r,'mxCell',id='0');E.SubElement(self.r,'mxCell',id='1',parent='0');self.n=1
 def node(self,x,y,w,h,label,style='',size=28):
  self.n+=1;i=str(self.n);c=E.SubElement(self.r,'mxCell',id=i,value=label,style=f'whiteSpace=wrap;html=0;fillColor=#FFFFFF;strokeColor=#31516E;fontFamily=Arial;fontSize={size};fontColor=#172B45;spacing=12;'+style,vertex='1',parent='1');E.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'});return i
 def edge(self,a,b,label='',style='',points=()):
  self.n+=1;c=E.SubElement(self.r,'mxCell',id=str(self.n),value=label,source=a,target=b,edge='1',parent='1',style='edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;endArrow=block;endFill=1;strokeColor=#31516E;fontColor=#172B45;fontFamily=Arial;fontSize=23;labelBackgroundColor=#FFFFFF;jettySize=25;'+style)
  g=E.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'})
  if points:
   ar=E.SubElement(g,'Array',attrib={'as':'points'})
   for x,y in points:E.SubElement(ar,'mxPoint',x=str(x),y=str(y))
 def export(self):
  if len(sys.argv)>1 and self.name not in sys.argv[1:]:return
  f=OUT/(self.name+'.drawio');E.ElementTree(self.root).write(f,encoding='utf-8',xml_declaration=True)
  subprocess.run(['/Applications/draw.io.app/Contents/MacOS/draw.io','--export','--format','png','--scale','1.3','--border','12','--output',str(f.with_suffix('.png')),str(f)],check=True,stdout=subprocess.DEVNULL)
def box(d,x,y,w,h,t):return d.node(x,y,w,h,t,'rounded=1;arcSize=12;')
# C4 system context: responsibilities, not a workflow timeline.
d=D('01-context')
p=box(d,20,120,310,180,'Professor\n[Person]\nPublishes materials and policy')
c=box(d,540,120,420,210,'Course Digital Twin\n[Software system]\nAnswers and continues support')
s=box(d,1170,120,310,180,'Student\n[Person]\nAsks, attempts and receives support')
m=box(d,570,440,360,110,'Generation provider\n[External software system]')
d.edge(p,c,'configures');d.edge(s,c,'uses');d.edge(c,m,'requests candidates', 'dashed=1;');d.export()
# C4 local architecture. Logical execution units; ingest service shown inside API responsibility.
d=D('02-containers',1500,610)
w=box(d,20,180,280,160,'Web application\n[React / browser]\nProfessor and student UI')
a=box(d,490,30,400,200,'API service\n[Python / FastAPI]\nCourse setup, ingestion,\ntutoring and authorized saves')
b=box(d,490,365,400,180,'Autonomy worker\n[Python]\nObserves activity and\nprocesses due support')
sq=d.node(1150,220,300,140,'SQLite\n[Data store]\nDialogue, goals and jobs','shape=cylinder3;size=15;')
f=box(d,1150,20,300,115,'File storage\n[Data store]\nSource materials')
md=box(d,1150,470,300,115,'Generation provider\n[External system]')
d.edge(w,a,'HTTPS / API');d.edge(a,sq,'reads / writes');d.edge(b,sq,'reads / writes');d.edge(a,f,'reads / writes');d.edge(b,md,'configured calls');d.edge(a,md,'configured calls',points=[(1020,130),(1020,525)]);d.export()
# Physical ER subset, verified against migrations.py. No goal-to-attribution FK.
d=D('03-erd',1500,570)
def ent(x,y,title,fields):return d.node(x,y,370,205,title+'\n────────────\n'+fields,'align=left;verticalAlign=top;',26)
u=ent(20,20,'Account','PK  id')
r=ent(20,345,'Published release','PK  id\nFK  course_id')
g=ent(555,20,'Learning goal','PK  goal_id\nFK  student_id, release_id')
c=ent(555,345,'Conversation','PK  id\nFK  student_id, release_id')
o=ent(1090,20,'Learner observation','PK  observation_id\nFK  conversation_id')
at=ent(1090,345,'Concept assessment','PK  conversation_id,\n      revision, concept_id\nFK  conversation_id')
style='startArrow=ERmandOne;startFill=0;endArrow=ERzeroToMany;endFill=0;'
d.edge(u,g,'',style+'exitX=1;exitY=0.3;entryX=0;entryY=0.3;');d.edge(u,c,'',style+'exitX=1;exitY=0.75;entryX=0;entryY=0.3;jumpStyle=arc;',[(440,170),(440,405)]);d.edge(r,c,'',style+'exitX=1;exitY=0.75;entryX=0;entryY=0.75;');d.edge(r,g,'',style+'exitX=1;exitY=0.3;entryX=0;entryY=0.75;jumpStyle=arc;',[(490,405),(490,170)]);d.edge(c,o,'',style+'exitX=1;exitY=0.3;entryX=0;entryY=0.5;',[(995,405),(995,120)]);d.edge(c,at,'',style+'exitX=1;exitY=0.75;entryX=0;entryY=0.5;');d.export()
# UML sequence with lifelines and ordered messages, overview with explicit participants.
def sequence(name,labels,messages):
 d=D(name,1500,600);xs=[30+i*500 for i in range(3)];ids=[]
 for x,label in zip(xs,labels):
  ids.append(d.node(x,10,380,65,label))
  d.node(x+189,75,1,510,'','fillColor=none;strokeColor=#91A4B7;dashed=1;')
 for k,(a,b,t) in enumerate(messages):
  y=140+k*85
  na=d.node(xs[a]+188,y,3,3,'','fillColor=none;strokeColor=none;');nb=d.node(xs[b]+188,y,3,3,'','fillColor=none;strokeColor=none;')
  d.edge(na,nb,t,'edgeStyle=none;fontSize=27;'+('endArrow=open;endFill=0;dashed=1;' if ('Return' in t or 'Reject' in t) else 'endArrow=block;endFill=1;'))
 d.export()
sequence('04-reactive',['Student','API / tutoring service','Saved state'],[(0,1,'1  Submit question or attempt'),(1,2,'2  Read release and learner records'),(2,1,'3  Return authorized context'),(1,2,'4  Recheck authority; save response'),(1,0,'5  Return saved answer')])
sequence('05-autonomous',['Autonomy worker','Support service','Saved state'],[(0,2,'1  Read activity and due work'),(0,1,'2  Process an eligible opportunity'),(1,2,'3  Check goal, consent and evidence'),(1,2,'4  Recheck; save message or no-action'),(1,0,'5  Record completion')])
# Current factual path, standard UML activities.
d=D('06-answer-path')
start=d.node(15,195,28,28,'','ellipse;fillColor=#172B45;');a=box(d,115,135,330,145,'Load the published\ncourse and allowed sources');b=box(d,555,135,330,145,'Rank evidence\nwith BM25');c=box(d,995,135,430,145,'Check evidence and assemble\nrequired supported facts')
d.edge(start,a);d.edge(a,b);d.edge(b,c)
d.node(535,355,920,110,'Ambiguous or insufficient evidence → clarify or abstain\nSuccessful response → save answer with source citations','shape=note;',27);d.export()
# Failure comparisons are independent UML activities, each has its own initial/final.
d=D('07-answer-alternatives',1500,580)
for i,(label,steps) in enumerate([('Simple control',['Keyword retrieval','Accept an evidence hit','Extract a response']),('Hierarchy',['Hierarchical retrieval','Check whole-question coverage','Answer or abstain']),('Plan and observe',['Decompose / retrieve / combine','Check whole-question coverage','Answer or abstain'])]):
 x=15+500*i;d.node(x,0,465,50,label,'strokeColor=none;fontStyle=1;',30);prev=d.node(x+215,65,25,25,'','ellipse;fillColor=#172B45;')
 for j,t in enumerate(steps):
  node=box(d,x+10,135+j*130,445,85,t);d.edge(prev,node);prev=node
 end=d.node(x+213,535,28,28,'','shape=endState;fillColor=#172B45;');d.edge(prev,end)
d.export()
# Guarded planner activity: fork avoided; explicit decisions and terminal outcomes.
d=D('08-guarded-planner',1500,580)
st=d.node(20,220,25,25,'','ellipse;fillColor=#172B45;');gate=d.node(110,155,200,155,'Evidence\nallowed?','rhombus;',27);a=box(d,400,170,315,130,'Keep permitted\nbaseline action A');b=box(d,810,170,315,130,'Evaluate proposal\nand predicted value');v=d.node(1210,155,240,170,'Replacement\nguards pass?','rhombus;',26)
no=box(d,40,440,300,100,'No action');keep=box(d,770,440,330,100,'Use baseline A');use=box(d,1185,440,300,100,'Use proposal')
d.edge(st,gate);d.edge(gate,a,'[yes]');d.edge(gate,no,'[no]');d.edge(a,b);d.edge(b,v);d.edge(v,use,'[yes]');d.edge(v,keep,'[no]',points=[(1160,370),(940,370)]);d.export()
# Goal state machine: only active has outgoing transitions; attempt cap not completion.
d=D('09-goal-states')
st=d.node(20,205,25,25,'','ellipse;fillColor=#172B45;');a=box(d,140,125,390,180,'Active\nMay produce bounded jobs');c=box(d,1110,10,340,100,'Completed');e=box(d,1110,230,340,100,'Expired');can=box(d,1110,450,340,100,'Cancelled')
d.edge(st,a);d.edge(a,c,'[all target evidence passes]',points=[(800,70)]);d.edge(a,e,'[expiry reached]');d.edge(a,can,'[cancelled / scope invalid]',points=[(800,485)])
d.node(100,405,660,110,'Sending a message increments attempts.\nAn attempt limit does not complete the goal.','shape=note;',29);d.export()
sequence('10-authority-change',['Tutoring service','Professor / release service','Saved state'],[(0,2,'1  Read current release and state'),(1,2,'2  Withdraw release'),(0,2,'3  Recheck current authority at commit'),(2,0,'4  Reject stale work; save no answer')])
sequence('11-retry',['Worker','Delivery service','Saved state'],[(0,1,'1  Process delivery key K'),(1,2,'2  Save message for K'),(0,1,'3  Restart; retry the same key K'),(1,2,'4  Look up existing message for K'),(2,1,'5  Return the saved message')])
# One readable sequence for the two entry points.
d=D('12-execution',1500,610)
xs=[15,395,775,1155]
for x,t in zip(xs,['Student','API / support service','Worker','Saved state']):
 d.node(x,0,325,60,t,size=27);d.node(x+162,60,1,540,'','fillColor=none;strokeColor=#91A4B7;dashed=1;')
for a,b,y,t in [(0,1,120,'Submit question / attempt'),(1,3,200,'Recheck authority; save response'),(2,3,370,'Read due work'),(2,1,455,'Process eligible support'),(1,3,540,'Recheck; save message or no-action')]:
 aa=d.node(xs[a]+161,y,3,3,'','strokeColor=none;fillColor=none;');bb=d.node(xs[b]+161,y,3,3,'','strokeColor=none;fillColor=none;');d.edge(aa,bb,t,'edgeStyle=none;endArrow=block;endFill=1;fontSize=27;')
d.node(490,265,900,55,'Later: support can begin without another student request','shape=note;',27)
d.export()
print('Exported 12 focused draw.io diagrams')
