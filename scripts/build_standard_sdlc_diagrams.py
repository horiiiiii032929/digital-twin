"""Generate standard-notation draw.io diagrams. Run with --export for images."""
import argparse
from pathlib import Path
import subprocess
import xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/presentation/diagrams/standard"
INK="#182B43"; BLUE="#2459A6"; LIGHT="#EAF1FB"; GRAY="#EDF0F3"
class Diagram:
    def __init__(self,name,title,scope):
        self.name=name;self.i=0;self.nodes={}
        self.d=E.Element("diagram",id=name,name=name)
        m=E.SubElement(self.d,"mxGraphModel",grid="1",gridSize="10",page="1",pageWidth="1600",pageHeight="1000",pageScale="1",background="#ffffff")
        self.r=E.SubElement(m,"root")
        E.SubElement(self.r,"mxCell",id="0");E.SubElement(self.r,"mxCell",id="1",parent="0")
        self.node(0,0,1600,1000,"","strokeColor=none;fillColor=#ffffff;",bind=False)
        self.text(50,26,1500,60,title,34,True)
        self.text(50,92,1500,52,scope,21)
    def node(self,x,y,w,h,label,style="",size=23,bind=True):
        self.i+=1;ident=f"n{self.i}"
        cell=E.SubElement(self.r,"mxCell",id=ident,parent="1",vertex="1",value=label,
          style=f"whiteSpace=wrap;html=0;fontFamily=Arial;fontSize={size};fontColor={INK};fillColor=#ffffff;strokeColor={INK};strokeWidth=1.5;align=center;verticalAlign=middle;spacing=10;"+style)
        E.SubElement(cell,"mxGeometry",x=str(x),y=str(y),width=str(w),height=str(h),attrib={"as":"geometry"})
        if bind:self.nodes[ident]=(x,y,w,h)
        return ident
    def text(self,x,y,w,h,label,size=21,bold=False):
        return self.node(x,y,w,h,label,f"strokeColor=none;fillColor=none;align=left;spacing=0;fontStyle={1 if bold else 0};",size,False)
    def line(self,a,b,label="",style="",points=(),offset=-16,source=None,target=None):
        self.i+=1
        c=E.SubElement(self.r,"mxCell",id=f"e{self.i}",parent="1",edge="1",value=label,
            style=f"edgeStyle=none;rounded=0;html=0;fontFamily=Arial;fontSize=19;fontColor={INK};strokeColor={INK};strokeWidth=1.5;endArrow=open;endFill=0;labelBackgroundColor=#ffffff;"+style)
        g=E.SubElement(c,"mxGeometry",relative="1",attrib={"as":"geometry"})
        for key,(x,y) in [("sourcePoint",a),("targetPoint",b)]:
            E.SubElement(g,"mxPoint",x=str(x),y=str(y),attrib={"as":key})
        E.SubElement(g,"mxPoint",x="0",y=str(offset),attrib={"as":"offset"})
        if points:
            ar=E.SubElement(g,"Array",attrib={"as":"points"})
            for x,y in points:E.SubElement(ar,"mxPoint",x=str(x),y=str(y))
        for end,node,point in [("source",source,a),("target",target,b)]:
            if node:
                x,y,w,h=self.nodes[node];pre="exit" if end=="source" else "entry"
                c.set(end,node);c.set("style",c.get("style")+f"{pre}X={(point[0]-x)/w};{pre}Y={(point[1]-y)/h};")
        return c
    def note(self,x,y,w,h,label,size=21):
        return self.node(x,y,w,h,label,"shape=note;size=18;align=left;spacing=14;",size,False)
    def foot(self,text):
        self.text(50,942,1500,42,text,18)
    def bind(self):
        for c in self.r.findall("mxCell[@edge='1']"):
            if c.get("source") and c.get("target"): continue
            g=c.find("mxGeometry")
            for end in ["source","target"]:
                if c.get(end):continue
                pt=g.find(f"mxPoint[@as='{end}Point']");px=float(pt.get("x"));py=float(pt.get("y"))
                for ident,(x,y,w,h) in reversed(self.nodes.items()):
                    if w>=1500:continue
                    if x<=px<=x+w and y<=py<=y+h and min(abs(px-x),abs(px-x-w),abs(py-y),abs(py-y-h))<1:
                        c.set(end,ident);pre="exit" if end=="source" else "entry"
                        c.set("style",c.get("style")+f"{pre}X={(px-x)/w};{pre}Y={(py-y)/h};")
                        break
    def life(self,x,label):
        return self.node(x-145,180,290,710,label,"shape=umlLifeline;perimeter=lifelinePerimeter;participant=rectangle;size=75;",22)
    def msg(self,sx,tx,y,label,sid,tid,reply=False):
        return self.line((sx,y),(tx,y),label,"dashed=1;endArrow=open;" if reply else "endArrow=block;endFill=1;",source=sid,target=tid)
    def fragment(self,x,y,w,h,op):
        self.node(x,y,w,h,"","fillColor=none;",bind=False)
        self.node(x,y,85,34,op,"shape=umlFrame;fillColor=#ffffff;align=left;",20,False)
    def state(self,x,y,w,h,label):
        return self.node(x,y,w,h,label,"rounded=1;arcSize=16;",25)
pages=[]

d=Diagram("01-c4-context","C4 System Context — Course Digital Twin","Scope: course teaching system · Configured external inference is optional")
d.node(60,235,300,155,"Professor\n[Person]\nConfigures and approves teaching","fillColor="+LIGHT+";strokeColor="+BLUE+";")
d.node(60,605,300,155,"Student\n[Person]\nAsks questions and uses support","fillColor="+LIGHT+";strokeColor="+BLUE+";")
d.node(635,380,365,220,"Course Digital Twin\n[Software System]\nCourse-grounded tutoring and\ngoverned continuing support","fillColor="+LIGHT+";strokeColor="+BLUE+";fontStyle=1;")
d.node(1250,400,290,180,"Model provider\n[External Software System]\nReturns configured\nplanning / wording proposals","fillColor="+GRAY+";",22)
d.line((360,310),(635,425),"Configures, reviews and publishes",points=[(500,310),(500,425)])
d.line((360,680),(635,555),"Requests tutoring and manages consent",points=[(500,680),(500,555)])
d.line((1000,490),(1250,490),"Requests inference\n[configured modes]")
d.note(635,700,905,115,"Scope note: synthetic / approved course use. The diagram does not assert a public deployment or real-student learning benefit.")
d.foot("Key: labelled boxes = people/systems; grey = external system; solid open arrow = directed relationship.")
pages.append(d)

d=Diagram("02-c4-containers","C4 Container — Course Digital Twin","Scope: logical applications and data stores · External inference is configuration-dependent")
d.node(360,155,1220,765,"","fillColor=none;dashed=1;",bind=False)
d.text(385,166,1160,32,"Course Digital Twin [Software System boundary]",21,True)
d.node(50,225,260,120,"Professor / Student\n[Person]\nUses course workspaces","",21)
d.node(400,230,300,115,"Web application\n[Container: React / TypeScript]\nRole-scoped interfaces","fillColor="+LIGHT+";",20)
d.node(400,440,300,120,"API application\n[Container: Python / FastAPI]\nAuthority and tutoring","fillColor="+LIGHT+";",20)
d.node(820,440,300,120,"Runtime records\n[Container: SQLite]\nReleases, turns, state and jobs","shape=cylinder3;size=12;fillColor="+LIGHT+";",20)
d.node(1220,440,300,120,"Source artifacts\n[Container: filesystem]\nApproved versioned content","shape=folder;tabWidth=65;tabHeight=15;fillColor="+LIGHT+";",20)
d.node(400,755,300,120,"Autonomy worker\n[Container: Python]\nPolls and processes due work","fillColor="+LIGHT+";",20)
d.node(820,755,300,120,"Ingestion worker\n[Container: Python]\nProcesses source jobs","fillColor="+LIGHT+";",20)
d.node(50,755,260,120,"Model provider\n[External Software System]\nConfigured inference","fillColor="+GRAY+";",20)
d.line((310,285),(400,285),"Operates\n[browser]",offset=-25)
d.line((550,345),(550,440),"Requests\n[HTTP / JSON]",offset=0)
d.line((700,500),(820,500),"Reads / writes\n[SQL]",offset=-28)
c=d.line((700,535),(1220,500),"Reads source artifacts [file I/O]",points=[(750,535),(750,650),(1170,650),(1170,500)])
c.find("mxGeometry").set("x","-0.65")
d.line((400,500),(310,785),"Requests inference\n[HTTPS / JSON]",points=[(335,500),(335,785)])
d.line((400,840),(310,840),"Inference\n[HTTPS]",offset=-25)
d.line((700,800),(850,560),"Claims / commits\n[SQL]",points=[(760,800),(760,700),(850,700)],offset=-10)
d.line((970,755),(970,560),"Claims source jobs\n[SQL]",offset=30)
d.line((1120,815),(1370,560),"Writes sources\n[file I/O]",points=[(1370,815)],offset=-16)
d.foot("Key: dashed system boundary; blue = internal container; grey = external system; cylinder/folder = data store; arrows = labelled relationships.")
pages.append(d)

d=Diagram("03-uml-course-activity","UML Activity — Course publication and student access","Scope: one course release · Activity partitions identify responsibility")
for x,w,title in [(50,450,"Professor"),(500,600,"Application"),(1100,450,"Student")]:
    d.node(x,170,w,735,"","fillColor=none;",bind=False);d.text(x+20,185,w-40,40,title,25,True)
d.node(240,245,26,26,"","ellipse;fillColor="+INK+";",bind=True)
d.state(100,310,330,75,"Provide sources and policy")
d.node(745,325,42,42,"","rhombus;",bind=True) # merge
d.state(610,420,330,75,"Prepare draft and preview")
d.state(100,420,330,75,"Review draft / revise")
d.state(610,555,330,70,"Run preflight")
d.node(745,675,50,50,"","rhombus;")
d.state(1135,770,350,75,"Open authorized conversation")
d.state(610,770,330,75,"Publish reviewed release")
d.line((253,271),(253,310))
d.line((430,347),(745,346))
d.line((766,367),(766,420))
d.line((610,457),(430,457))
d.line((265,495),(610,590),"Request preflight",points=[(265,590)])
d.line((775,625),(770,675))
d.line((745,700),(745,346),"[blockers remain]",points=[(555,700),(555,346)],offset=0)
d.state(100,770,330,75,"Request publication")
d.line((770,725),(265,770),"[checks pass]",points=[(265,725)],offset=-12)
d.line((430,807),(610,807))
d.line((940,807),(1135,807),"[active membership]",offset=-20)
d.node(1300,870,30,30,"","ellipse;",bind=True);d.node(1306,876,18,18,"","ellipse;fillColor="+INK+";",bind=False)
d.line((1315,845),(1315,870))
d.foot("Notation: rounded action; diamond = merge/decision; [guard] = branch condition; filled circle = initial; bullseye = activity final.")
pages.append(d)

d=Diagram("04-uml-domain-classes","UML Class — Course, conversation and autonomous work","Scope: conceptual domain model · Selected identifiers only; implementation methods are omitted")
def cls(x,y,title,attrs):
    ident=d.node(x,y,370,150,"","",bind=True)
    d.text(x+15,y+8,340,35,title,24,True)
    d.line((x,y+50),(x+370,y+50),"","endArrow=none;",offset=0)
    d.text(x+15,y+62,340,80,attrs,21)
    return ident
cls(50,195,"Course","id\nowner_professor_id")
cls(615,195,"Release","id\ncourse_id\nstatus")
cls(1180,195,"Goal","goal_id\nstudent_id, release_id\nstatus")
cls(50,490,"Membership","account_id, course_id\nrole\nactive")
cls(615,490,"Conversation","id\nstudent_id, release_id")
cls(1180,490,"Opportunity","opportunity_id\ngoal_id [0..1]\nidempotency_key")
cls(615,775,"Message","id\nconversation_id\nclient_request_id")
cls(1180,775,"Citation","id\nmessage_id\nsource version / locator")
def assoc(a,b,label,start,end,points=()):
    d.line(a,b,label,"endArrow=none;",points=points,offset=-17)
    if a[1]==b[1]:
        d.text(a[0]+8,a[1]+5,65,28,start,19);d.text(b[0]-70,b[1]+5,65,28,end,19)
    else:
        d.text(a[0]+12,a[1]+3,65,28,start,19);d.text(b[0]+12,b[1]-30,65,28,end,19)
assoc((420,270),(615,270),"releases","1","0..*")
assoc((985,270),(1180,270),"goals","1","0..*")
assoc((235,345),(235,490),"memberships","1","0..*")
assoc((800,345),(800,490),"conversations","1","0..*")
assoc((1365,345),(1365,490),"opportunities","0..1","0..*")
assoc((800,640),(800,775),"messages","1","0..*")
assoc((985,850),(1180,850),"citations","1","0..*")
d.foot("Notation: class name / attribute compartments; solid association; endpoint multiplicities. Each opportunity may reference no goal.")
pages.append(d)

d=Diagram("05-uml-publication-sequence","UML Sequence — Preflight and publication","Scope: successful publication of an owned draft; blockers return to revision")
xs=[190,590,1010,1410]; ids=[d.life(x,t) for x,t in zip(xs,["professor:Workspace","publication:Service","release:Repository","index:Adapter"])]
for y,a,b,text,ret in [
(290,0,1,"requestPreflight(releaseId)",False),
(355,1,3,"prepareIndex() [if configured]",False),
(410,3,1,"index reference / result",True),
(470,1,2,"savePreflight(checks, evaluation)",False),
(525,1,0,"checks and blockers",True),
(650,0,1,"publish(releaseId)",False),
(710,1,2,"publishRelease() — recheck authority",False),
(765,2,1,"published release",True),
(835,1,0,"publication result",True)]:
    d.msg(xs[a],xs[b],y,text,ids[a],ids[b],ret)
d.fragment(50,573,1090,290,"opt")
d.text(155,580,940,33,"[preflight passes and professor requests publication]",18)
d.note(70,875,1460,55,"Repository transaction: replace current release, withdraw predecessor and cancel old work. Index preparation and post-publication hook are outside it.",19)
d.foot("Notation: dashed lifeline; filled arrow = synchronous call; dashed open arrow = reply; opt frame = guarded interaction.")
pages.append(d)

d=Diagram("06-uml-tutoring-sequence","UML Sequence — Tutoring and authority at commit","Scope: a fresh request reaching generation; policy/evidence boundary responses are omitted")
xs=[185,575,985,1400];ids=[d.life(x,t) for x,t in zip(xs,["student:Workspace","tutoring:Service","state:Repository","generator:Adapter"])]
for y,a,b,text,ret in [
(285,0,1,"submit(content, requestId)",False),
(350,1,2,"authorize; load scoped release and state",False),
(410,2,1,"authorized snapshot",True),
(480,1,3,"generate(selected evidence, policy, intent)",False),
(540,3,1,"response proposal",True),
(630,1,2,"saveTurn(expectedRevision) — recheck authority",False)]:
    d.msg(xs[a],xs[b],y,text,ids[a],ids[b],ret)
d.fragment(50,665,1075,255,"alt")
d.text(150,674,920,32,"[authority valid and expected revision matches]",18)
d.msg(985,575,730,"committed response, citations and state",ids[2],ids[1],True)
d.msg(575,185,770,"saved turn",ids[1],ids[0],True)
d.line((50,790),(1125,790),"","endArrow=none;dashed=1;",offset=0)
d.text(150,795,920,30,"[authority revoked or revision conflict]",18)
d.msg(985,575,845,"authority / revision error",ids[2],ids[1],True)
d.msg(575,185,895,"error; no accepted turn commit",ids[1],ids[0],True)
d.note(1135,645,405,215,"Generation is outside the write transaction.\n\nThe service validates the proposal before saveTurn().",21)
d.foot("Notation: synchronous calls / dashed replies; alt operands have exclusive guards. Matching duplicate requests return the saved turn.")
pages.append(d)

d=Diagram("07-uml-goal-state-machine","UML State Machine — Autonomous goal lifecycle","Scope: governed goal record · Completion guard shown for the evidence-count learner state")
d.node(120,420,30,30,"","ellipse;fillColor="+INK+";",bind=True)
d.state(340,365,360,150,"active")
d.state(1150,200,330,100,"completed")
d.state(1150,485,330,100,"expired")
d.state(1150,775,330,100,"cancelled")
d.line((150,435),(340,435),"/ initialize goal")
c=d.line((700,400),(1150,250),"assessmentCommitted [completionGuard]",points=[(930,400),(930,250)])
c.find("mxGeometry").set("x","-0.1")
d.line((700,475),(1150,535),"expirySweep [now ≥ expires_at]",points=[(965,475),(965,535)])
c=d.line((700,500),(1150,825),"scopeInvalidated / cancel pending work",points=[(850,500),(850,825)])
c.find("mxGeometry").set("x","0.7")
d.note(60,610,725,135,"Attempt limit reached: further work is blocked;\nthe goal remains active.\nThere is no exhausted state.",23)
d.note(900,620,640,110,"Terminal records do not transition back to active.\nA new goal requires a new record.",22)
d.note(60,175,780,130,"completionGuard: valid exact objective mapping; every target\nconcept has ≥ 2 correct, 0 incorrect and confidence ≥ 0.5.\nMissing or ambiguous evidence leaves the goal active.",22)
d.foot("Notation: filled circle = initial pseudostate; rounded rectangle = state; trigger [guard] / effect. Terminal records remain persisted.")
pages.append(d)

d=Diagram("08-uml-recovery-sequence","UML Sequence — Retry after an in-app delivery is saved","Scope: one stable delivery identity; local persistence recovery, not external exactly-once delivery")
xs=[220,770,1350];ids=[d.life(x,t) for x,t in zip(xs,["worker:AutonomyService","outreach:Service","runtime:Repository"])]
for y,a,b,text,ret in [
(290,0,1,"processTrigger(stableKey)",False),
(350,1,2,"save delivery after authority checks",False),
(410,2,1,"saved message",True),
(465,1,0,"delivery result",True)]:
    d.msg(xs[a],xs[b],y,text,ids[a],ids[b],ret)
d.note(70,505,1450,60,"Failure scenario: worker stops before commitAutonomousJob(). The in-app message is already persisted.",21)
d.fragment(60,600,1480,310,"opt")
d.text(175,607,1300,33,"[worker restarts and lease is recovered]",20)
for y,a,b,text,ret in [
(680,0,1,"processTrigger(same stableKey)",False),
(735,1,2,"find existing delivery",False),
(780,2,1,"existing saved message",True),
(825,1,0,"duplicate / existing message",True),
(885,0,2,"commitAutonomousJob(reconciled outcome)",False)]:
    d.msg(xs[a],xs[b],y,text,ids[a],ids[b],ret)
d.foot("Notation: calls and replies on lifelines; UML note marks the crash window; stable key identifies the saved message on retry.")
pages.append(d)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--export",action="store_true");args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    root=E.Element("mxfile",host="app.diagrams.net",agent="Codex",version="30.0.4")
    for d in pages:d.bind();root.append(d.d)
    E.indent(root);source=OUT/"sdlc-standard-diagrams.drawio"
    E.ElementTree(root).write(source,encoding="utf-8",xml_declaration=True)
    if args.export:
        app="/Applications/draw.io.app/Contents/MacOS/draw.io"
        for i,d in enumerate(pages,1):
            for fmt in ["png","svg"]:
                subprocess.run([app,"--export","--page-index",str(i),"--format",fmt,"--scale","1.5","--embed-diagram","--output",str(OUT/f"{d.name}.{fmt}"),str(source)],check=True)
        subprocess.run([app,"--export","--all-pages","--format","pdf","--output",str(OUT/"sdlc-standard-diagrams.pdf"),str(source)],check=True)
    print(source)
if __name__=="__main__":main()
