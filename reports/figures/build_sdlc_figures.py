"""Build vector SDLC figures at the manuscript's final reading size.

Run with Python + reportlab from the repository root. Diagram wording describes
the inspected implementation; these drawings do not execute application code.
Coordinates are points from the upper left; all figures are 452 points wide.
Monochrome: responsibilities and outcomes use labels/shapes, never hue.
"""
from pathlib import Path
import json
import math
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.colors import HexColor, white

OUT = Path(__file__).resolve().parent
W = 452
INK = "#111111"
LINE = "#333333"
BLUE = "#FFFFFF"
TEAL = "#FFFFFF"
AMBER = "#FFFFFF"
GREY = "#F3F3F3"
RED = "#FFFFFF"
AUDIT = []


class Diagram:
    def __init__(self, name, height, title, subtitle):
        self.name, self.h = name, height
        self.c = canvas.Canvas(str(OUT / (name + ".pdf")), pagesize=(W, height - 42),
                               pageCompression=1, pdfVersion=(1, 5), invariant=1)
        self.c.setTitle(title)
        self.c.setAuthor("Hikaru (Rawin) Horinouchi")
        self.boxes = {}
        self.minfont = 9.8

    def text(self, x, y, s, size=10, bold=False, color=INK, align="left"):
        c = self.c
        c.setFillColor(HexColor(color))
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        width = stringWidth(s, font, size)
        if align == "center":
            x -= width / 2
        if align == "right":
            x -= width
        assert x >= -0.5 and x + width <= W + .5, (self.name, s, x, width)
        assert 0 <= y <= self.h, (self.name, s, y)
        c.drawString(x, self.h - y, s)

    def wrap(self, s, width, size, bold=False):
        font = "Helvetica-Bold" if bold else "Helvetica"
        lines = []
        for paragraph in s.split("\n"):
            line = ""
            for word in paragraph.split():
                test = (line + " " + word).strip()
                if stringWidth(test, font, size) <= width:
                    line = test
                else:
                    assert line, (self.name, word, width)
                    lines.append(line)
                    line = word
            lines.append(line)
        return lines

    def para(self, x, y, width, s, size=10, leading=12.5, bold=False, align="left"):
        lines = self.wrap(s, width, size, bold)
        for i, line in enumerate(lines):
            self.text(x + (width / 2 if align == "center" else 0),
                      y + i * leading, line, size, bold, align=align)
        return len(lines) * leading

    def rect(self, x, y, w, h, fill=GREY, stroke=LINE, radius=0, dash=False):
        c = self.c
        c.setFillColor(HexColor(fill) if fill else white)
        c.setStrokeColor(HexColor(stroke))
        c.setLineWidth(.8)
        c.setDash(4, 3) if dash else c.setDash()
        if radius:
            c.roundRect(x, self.h-y-h, w, h, radius, fill=int(bool(fill)), stroke=1)
        else:
            c.rect(x, self.h-y-h, w, h, fill=int(bool(fill)), stroke=1)
        c.setDash()

    def box(self, key, x, y, w, h, title, body="", fill=BLUE, rounded=True):
        self.rect(x, y, w, h, fill, radius=5 if rounded else 0)
        titlelines = self.wrap(title, w-14, 10.4, True)
        bodylines = self.wrap(body, w-14, 10) if body else []
        needed = len(titlelines)*12.5 + len(bodylines)*12 + (4 if body else 0)
        assert needed <= h-10, (self.name, key, needed, h)
        base = y+(h-needed)/2+9
        for line in titlelines:
            self.text(x+w/2, base, line, 10.4, True, align="center")
            base += 12.5
        if body:
            base += 4
            for line in bodylines:
                self.text(x+w/2, base, line, 10, align="center")
                base += 12
        self.boxes[key] = (x,y,w,h)

    def port(self, key, side):
        x,y,w,h = self.boxes[key]
        return {"T":(x+w/2,y), "B":(x+w/2,y+h),
                "L":(x,y+h/2), "R":(x+w,y+h/2)}[side]

    def line(self, points, dashed=False, arrow=True, color=LINE, width=.9, open_head=False):
        c = self.c
        c.setStrokeColor(HexColor(color)); c.setFillColor(HexColor(color))
        c.setLineWidth(width)
        c.setDash(4,3) if dashed else c.setDash()
        p=c.beginPath();p.moveTo(points[0][0],self.h-points[0][1])
        for x,y in points[1:]:
            p.lineTo(x,self.h-y)
        c.drawPath(p);c.setDash()
        if arrow:
            x,y=points[-1];px,py=points[-2]
            theta=math.atan2(y-py,x-px)
            p=c.beginPath();p.moveTo(x,self.h-y)
            for sign in [-1,1]:
                bx=x-5.3*math.cos(theta)+sign*2.3*math.sin(theta)
                by=y-5.3*math.sin(theta)-sign*2.3*math.cos(theta)
                if open_head:p.moveTo(x,self.h-y)
                p.lineTo(bx,self.h-by)
            if open_head:
                c.drawPath(p,fill=0,stroke=1)
            else:
                p.close();c.drawPath(p,fill=1,stroke=0)

    def connect(self, a, b, sa="B", sb="T", via=(), **kwargs):
        self.line([self.port(a,sa),*via,self.port(b,sb)],**kwargs)

    def label(self, x, y, s, size=9.8, align="center"):
        width=stringWidth(s,"Helvetica",size)
        left=x-width/2 if align=="center" else x
        self.c.setFillColor(white)
        self.c.rect(left-2,self.h-y-2,width+4,size+3,fill=1,stroke=0)
        self.text(x,y,s,size,align=align)

    def diamond(self, key, x, y, w, h, text):
        c=self.c;c.setFillColor(HexColor(AMBER));c.setStrokeColor(HexColor(LINE));c.setLineWidth(.9)
        p=c.beginPath()
        p.moveTo(x,self.h-y-h/2);p.lineTo(x+w/2,self.h-y)
        p.lineTo(x+w,self.h-y-h/2);p.lineTo(x+w/2,self.h-y-h);p.close()
        c.drawPath(p,fill=1,stroke=1)
        lines=text.split("\n")
        for i,s in enumerate(lines):
            self.text(x+w/2,y+h/2+(i-(len(lines)-1)/2)*11+3,s,10,True,align="center")
        self.boxes[key]=(x,y,w,h)

    def dot(self,x,y,final=False):
        c=self.c;c.setFillColor(HexColor(INK));c.setStrokeColor(HexColor(INK))
        c.circle(x,self.h-y,3.2,fill=1,stroke=0)
        if final:c.circle(x,self.h-y,5.5,fill=0,stroke=1)

    def lanes(self, names, bottom):
        for i,name in enumerate(names):
            x=4+i*150
            self.rect(x,48,144,bottom-48,fill=None,stroke="#BBBBBB")
            self.rect(x,48,144,25,fill=GREY,stroke="#BBBBBB")
            self.text(x+72,65,name,10.4,True,align="center")

    def frame(self,x,y,w,h,kind,guard="",fill=None):
        self.rect(x,y,w,h,fill)
        tagw=stringWidth(kind,"Helvetica-Bold",9.8)+14
        self.rect(x,y,tagw,17,GREY)
        self.text(x+6,y+12,kind,9.8,True)
        if guard:self.text(x+tagw+7,y+12,guard,9.8)

    def finish(self):
        self.c.save()
        AUDIT.append({"file":self.name+".pdf","width_pt":W,"height_pt":self.h-42,
                      "minimum_font_pt":9.8,"boxes":len(self.boxes)})


def lifecycle():
    d=Diagram("course-twin-lifecycle",568,"Course lifecycle | Activity view",
              "Three responsibilities; downward progress follows one course release.")
    d.lanes(["Professor","Application","Student"],563)
    d.dot(76,83)
    d.box("setup",8,98,136,62,"Configure course","Sources, permissions,\nteaching preferences")
    d.line([(76,87),(76,98)])
    d.box("ingest",158,175,136,48,"Prepare draft","Parse + bind versions")
    d.connect("setup","ingest","R","T",via=[(226,129)])
    d.box("preview",8,239,136,50,"Review preview","Revise source / policy")
    d.connect("ingest","preview","B","T",via=[(226,231),(76,231)])
    d.diamond("checks",174,305,104,52,"Preflight\npasses?")
    d.connect("preview","checks","B","T",via=[(76,297),(226,297)])
    d.connect("checks","preview","L","L",via=[(1,331),(1,264)])
    d.label(131,325,"[no]")
    d.box("publish",8,377,136,48,"Approve + publish","Explicit instructor act")
    d.connect("checks","publish","B","T",via=[(226,366),(76,366)])
    d.label(150,364,"[yes]")
    d.box("release",158,377,136,48,"Activate release","Recheck + persist")
    d.connect("publish","release","R","L")
    d.box("access",308,439,136,48,"Select course","Membership + release")
    d.connect("release","access","R","T",via=[(376,401)])
    d.box("chat",308,492,136,43,"Ask / attempt","Inspect cited evidence")
    d.connect("access","chat")
    d.box("review",8,487,136,48,"Review difficulties","Revise next release")
    d.connect("chat","review","L","R",via=[(226,513),(226,511)])
    d.label(227,500,"saved signals")
    d.box("consent",308,98,136,98,"Separate preference",
          "Enable, snooze or\nwithdraw proactive\nsupport. Ordinary chat\ndoes not opt in.",fill=TEAL)
    d.line([(76,535),(76,546.5)]);d.dot(76,552,True)
    d.finish()


def architecture():
    d=Diagram("course-twin-architecture",630,"Logical architecture | Runtime boundary and components",
              "C4-inspired responsibilities. Arrows are labelled dependencies, not a deployment topology.")
    d.box("web",8,52,202,54,"Web workspace [React]","Professor + student interface",rounded=False)
    d.box("workers",242,52,202,54,"Workers [Python processes]","Ingestion jobs; autonomy polls",rounded=False)
    d.rect(4,142,444,378,fill=None,stroke=LINE)
    d.label(226,153,"Shared Python application code")
    d.box("api",18,171,180,46,"API entry [FastAPI]","Authenticate + validate",rounded=False)
    d.box("entry",254,171,180,46,"Worker entry points","Observe / claim due work",rounded=False)
    d.connect("web","api",via=[(109,125),(108,125)])
    d.label(108,132,"HTTP(S)")
    d.connect("workers","entry",via=[(343,125),(344,125)])
    d.label(344,132,"scheduled execution")
    d.box("govern",18,255,416,54,"Course authority + application orchestration",
          "Publication, tutoring and outreach services [Python]",rounded=False)
    d.connect("api","govern",via=[(108,237),(226,237)])
    d.connect("entry","govern",via=[(344,237),(226,237)])
    d.box("reactive",18,350,192,104,"Tutoring components",
          "Retrieve [BM25]\nSelect evidence + intent\nGenerate / validate response\nPrepare learner update",rounded=False)
    d.box("proactive",242,350,192,104,"Autonomy components",
          "Goal + opportunity observer\nGuarded action planner\nGenerate / validate wording\nAuthorize delivery",rounded=False)
    d.line([(116,309),(116,350)]);d.label(116,334,"student turn")
    d.line([(338,309),(338,350)]);d.label(338,334,"due opportunity")
    d.box("store",8,564,202,56,"Persistence + artifacts","SQLite domain / checkpoints;\nlocal source files",fill=AMBER,rounded=False)
    d.box("provider",242,564,202,56,"External model provider","Provider adapters [HTTPX]\nResponses API when configured",fill=TEAL,rounded=False)
    d.box("contracts",18,477,416,33,"Repository contracts + provider adapters",fill=GREY,rounded=False)
    d.line([(114,454),(114,477)]);d.line([(338,454),(338,477)])
    d.line([(114,510),(114,564)]);d.label(114,540,"read / commit state")
    d.line([(338,510),(338,564)]);d.label(338,540,"bounded model requests")
    d.finish()


def sequence(name, publication=False):
    title="Publication | UML sequence view" if publication else "Tutoring turn | UML sequence view"
    d=Diagram(name,570,title,"Solid arrow: call; dashed arrow: return. Time flows downward; critical frame marks commit.")
    xs=[44,162,292,410]
    labels=["Professor\nworkspace","Publication\nservice","Release\nrepository","Index\nadapter"] if publication else [
        "Student\nworkspace","Tutoring\nservice","Repository /\nretrieval","Generator\nadapter"]
    for i,(x,label) in enumerate(zip(xs,labels)):
        d.box("p"+str(i),x-39,52,78,42,label,fill=GREY,rounded=False)
        d.line([(x,94),(x,559)],dashed=True,arrow=False,color="#777777",width=.65)
    spans = [(1,143,288),(1,351,558),(2,244,260),(2,439,489),
             (3,180,196),(3,385,398)] if publication else [
             (1,120,555),(2,155,188),(3,298,329),(2,476,519)]
    for actor,start,end in spans:
        d.rect(xs[actor]-3,start,6,end-start,fill=GREY)
    def active(actor,y):
        return any(a == actor and start <= y <= end for a,start,end in spans)
    def msg(a,b,y,s,reply=False):
        direction=1 if b>a else -1
        start=xs[a]+direction*3 if active(a,y) else xs[a]
        end=xs[b]-direction*3 if active(b,y) else xs[b]
        d.line([(start,y),(end,y)],dashed=reply,open_head=reply)
        d.label((xs[a]+xs[b])/2,y-7,s)
    def selfcall(a,y,s):
        x=xs[a];d.line([(x+3,y),(x+24,y),(x+24,y+15),(x+3,y+15)])
        d.label(x+31,y+10,s,align="left")
    if not publication:
        msg(0,1,120,"1 Submit turn")
        msg(1,2,155,"2 Scope + state")
        msg(2,1,188,"3 Evidence",True)
        selfcall(1,207,"4 Select support + intent")
        d.frame(7,244,438,149,"alt","evidence / policy branch")
        d.text(16,278,"[supported]",9.8,True)
        msg(1,3,298,"5 Generate from selected evidence")
        msg(3,1,329,"6 Response + claim/source IDs",True)
        d.line([(7,343),(445,343)],dashed=True,arrow=False,color="#777777")
        d.text(16,366,"[insufficient / restricted]",9.8,True)
        selfcall(1,370,"Select clarify / abstain / refuse")
        selfcall(1,413,"7 Validate; prepare turn artifacts")
        d.frame(123,444,322,85,"critical","serialized turn commit",fill=None)
        msg(1,2,476,"8 Save turn")
        d.para(298,479,139,"Recheck authority + revision;\nsave response and state.",9.8,12)
        msg(2,1,519,"9 Saved / conflict",True)
        msg(1,0,555,"10 Reply / error",True)
    else:
        d.label(105,118,"Preflight readiness phase")
        msg(0,1,143,"1 Preflight")
        msg(1,3,180,"2 Prepare index when configured")
        selfcall(1,202,"3 Check sources + profile")
        msg(1,2,244,"4 Save audit")
        msg(1,0,288,"5 Check results",True)
        d.para(16,308,420,"[blockers] Revise the draft and repeat preflight.\n[ready] The professor may issue a separate publication request.",9.8,12)
        msg(0,1,351,"6 Publish")
        msg(1,3,385,"7 Recheck readiness; prepare index")
        d.frame(123,406,322,94,"critical","publication transaction")
        msg(1,2,439,"8 Publish release")
        d.para(298,444,138,"Recheck authority;\nreplace current release;\ncancel obsolete work.",9.8,12)
        msg(2,1,489,"9 Committed",True)
        selfcall(1,518,"Post-publication observer")
        msg(1,0,558,"10 Published",True)
    d.finish()


def learner():
    d=Diagram("course-twin-learner-state",388,"Two state consumers | Assessment and planning",
              "The current product uses different inputs for goal completion and for action planning.")
    d.box("turn",8,57,210,62,"Committed student evidence",
          "One unambiguous primary concept\nper assessed turn",fill=BLUE)
    d.box("job",242,57,202,62,"Job snapshot",
          "Delivered goal actions +\nsupporting observation IDs",fill=AMBER)
    d.box("counts",8,149,210,67,"Concept counters",
          "2 correct, 0 incorrect; assessed = 2\nConfidence q = 2 / (2 + 2) = 0.5",fill=BLUE)
    d.box("proxy",242,149,202,67,"Default planner proxy",
          "d = 0, k = 2\np_plan = 0.5; u_plan = 1/3",fill=AMBER)
    d.connect("turn","counts");d.connect("job","proxy")
    d.box("complete",8,246,210,62,"Goal completion",
          "Require eligible evidence for\nevery target concept",fill=TEAL)
    d.box("plan",242,246,202,62,"Action utility",
          "Score permitted interventions;\nnot assessed mastery",fill=AMBER)
    d.connect("counts","complete");d.connect("proxy","plan")
    d.box("example",8,332,436,48,"Same record; different objectives",
          "Cache-coherence goal: complete. Unassessed virtual-memory goal: remain active.",fill=GREY)
    d.finish()


def planner():
    d=Diagram("course-twin-planner-decision",558,"Guarded planner | Decision logic with a worked example",
              "Code-derived example, not a saved model response. State: repeated confusion; evidence ready.")
    d.box("policy",8,62,136,86,"Instructor policy",
          "Permits hint and\ndiagnostic question",fill=BLUE)
    d.box("event",158,62,136,86,"Event rule",
          "Fallback order:\nhint, then question",fill=BLUE)
    d.box("state",308,62,136,86,"Default state",
          "d = 0; k = 2\np = 0.5; u = 1/3",fill=AMBER)
    d.box("eligible",8,179,436,45,"1  Form eligible action set",
          "Event actions intersect instructor permission; include no action.",fill=BLUE)
    for x in [76,226,376]:d.line([(x,148),(x,179)])
    d.diamond("ready",166,245,120,50,"Evidence\nready?")
    d.connect("eligible","ready")
    d.box("none",329,245,115,49,"No action","[not ready]",fill=RED)
    d.connect("ready","none","R","L")
    d.box("scores",8,321,226,99,"2  Analytic scoring",
          "Hint / example       U = 0.325\nDiagnostic question  U = 0.267\nNo action            U = 0.000\nBaseline and best action: hint",fill=TEAL)
    d.box("model",264,321,180,99,"3  Bounded model proposal",
          "Can propose an action and steps.\nExample: diagnostic question.\nReject non-permitted steps.",fill=BLUE)
    d.connect("ready","scores",via=[(226,307),(121,307)])
    d.connect("ready","model",via=[(226,307),(354,307)])
    d.label(226,304,"[ready]")
    d.diamond("promote",117,438,219,63,"Proposal = analytic best\nAND gain over fallback\nat least 0.04?")
    d.connect("scores","promote",via=[(121,428),(226,428)])
    d.connect("model","promote",via=[(354,428),(226,428)])
    d.box("keep",8,519,210,32,"Retain hint in this example",fill=TEAL)
    d.box("use",242,519,202,32,"Use qualifying model proposal",fill=BLUE)
    d.connect("promote","keep","L","T",via=[(113,470)])
    d.label(91,503,"[no]")
    d.connect("promote","use","R","T",via=[(343,470)])
    d.label(367,503,"[yes]")
    d.finish()


def autonomy():
    d=Diagram("course-twin-autonomy",599,"Proactive support | Activity across two time periods",
              "One bounded job ends before a later response or scheduled event can start another.")
    d.lanes(["Worker","Planner + graph","Delivery / turn service"],513)
    d.dot(76,84)
    d.box("observe",8,99,136,58,"1 Observe","Saved event / due time;\nignore terminal goals")
    d.line([(76,88),(76,99)])
    d.box("claim",8,181,136,47,"2 Claim opportunity","Expiring worker lease")
    d.connect("observe","claim")
    d.box("plan",158,181,136,47,"3 Select action","Guarded planner")
    d.connect("claim","plan","R","L")
    d.diamond("auth",171,264,110,58,"Action\neligible?")
    d.connect("plan","auth")
    d.box("stop",308,264,136,58,"No delivery","Record blocked /\nfailed outcome",fill=RED)
    d.connect("auth","stop","R","L")
    d.label(294,284,"[no]")
    d.dot(376,343,True);d.line([(376,322),(376,337)])
    d.box("word",158,356,136,66,"4 Generate + check",
          "Approved evidence;\none bounded repair;\nuncertain call: stop")
    d.connect("auth","word");d.label(226,345,"[yes]")
    d.box("deliver",308,356,136,66,"5 Deliver",
          "Recheck authority;\npersist message with\nstable delivery key",fill=TEAL)
    d.connect("word","deliver","R","L")
    d.box("outcome",8,447,136,39,"6 Commit job result","Action / outcome records")
    d.connect("deliver","outcome","B","T",via=[(376,438),(76,438)])
    d.label(226,434,"delivery precedes job-result commit")
    d.line([(294,408),(300,408),(300,253),(376,253),(376,264)])
    d.label(344,248,"[invalid / uncertain]")
    d.line([(76,486),(76,494.5)]);d.dot(76,500,True)
    d.line([(4,527),(448,527)],dashed=True,arrow=False)
    d.label(226,530,"LATER RESPONSE OR SCHEDULED EVENT")
    d.box("new",8,548,192,43,"Start a new bounded job","Re-evaluate the active goal",fill=GREY)
    d.box("reply",242,542,202,55,"Commit learner evidence",
          "Check objective-specific completion;\nterminal goals receive no further work.",fill=TEAL)
    d.connect("reply","new","L","R")
    d.finish()


def failure():
    d=Diagram("course-twin-evidence-failure",394,"Why the selected gate failed at corpus scale",
              "Schematic of the recorded failure mechanism; boxes are evidence candidates, not new observations.")
    d.rect(4,53,218,265,fill=None,stroke="#999999")
    d.rect(230,53,218,265,fill=None,stroke="#999999")
    d.text(113,72,"Single-chunk confirmation",10.4,True,align="center")
    d.text(339,72,"Whole-corpus regression",10.4,True,align="center")
    d.box("one",16,91,194,65,"One approved chunk",
          "Only claim class A is available.",fill=BLUE)
    d.box("many",242,91,194,65,"Several approved chunks",
          "A: strongest relevant region\nB: weaker, different claim class",fill=BLUE)
    d.box("gate1",16,184,194,59,"Original ambiguity gate",
          "Only one class clears the test:\nno competing class.",fill=GREY)
    d.box("gate2",242,184,194,59,"Same ambiguity gate",
          "A and B both clear coverage:\ntreat as competing claims.",fill=GREY)
    d.connect("one","gate1");d.connect("many","gate2")
    d.box("ans",16,270,194,35,"Answer path remains open",fill=TEAL)
    d.box("clarify",242,270,194,35,"Return clarification",fill=RED)
    d.connect("gate1","ans");d.connect("gate2","clarify")
    d.box("result",8,336,436,52,"Recorded diagnostic",
          "6,973 / 10,000 cases clarified. In the 100-case probe, 84 retrieved the correct\nregion first; 69 still clarified. This motivated dominance-scoped comparison.",fill=AMBER)
    d.finish()


def simulation():
    d=Diagram("course-twin-simulation-design",464,"Learner / timing comparison",
              "Fit on development seeds, freeze parameters, then compare the same held-out learner grid.")
    d.box("fit",8,55,184,70,"Development fit",
          "6 seeds; observed next-answer loss\nChoose estimator parameters",fill=GREY)
    d.box("held",260,55,184,70,"Held-out grid",
          "6 personas x 2 simulator families\nx 20 seeds = 240 histories / condition",fill=BLUE)
    d.connect("fit","held","R","L");d.label(226,84,"freeze")
    d.box("grid",8,151,436,68,"Eleven conditions; 30 virtual days; eight concepts",
          "Count / BKT / PFA  x  constant / conditional / value timing = nine\nTwo bounds: oracle timing and never intervene",fill=BLUE)
    d.line([(343,125),(343,151)])
    d.text(8,244,"Inside each learner history",10.4,True)
    d.box("agent",8,268,184,70,"Estimator + timing",
          "Update estimate from observed\nanswers; choose an intervention\nor no action.",fill=BLUE)
    d.box("world",260,268,184,70,"Simulated learner",
          "Hidden mastery, receptivity\nand forgetting determine\nsubsequent responses.",fill=AMBER)
    d.connect("agent","world","R","L")
    d.label(226,295,"action")
    d.connect("world","agent","B","B",via=[(352,364),(100,364)])
    d.label(226,361,"observed response only")
    d.box("score",8,395,436,63,"Separate scorer",
          "Compare estimates with hidden state: MSE, wasted-message fraction,\nfinal hidden mastery. Only the oracle bound can use hidden state to act.",fill=TEAL)
    d.line([(416,338),(416,395)],dashed=True)
    d.label(411,382,"truth")
    d.finish()


def data():
    d=Diagram("course-twin-data-relationships",470,"Persistent information | Conceptual data model",
              "Upper panel: stored references (multiplicities at endpoints). Lower panel: evidence updates.")
    d.text(8,59,"A  Stored identity and references",10.4,True)
    d.box("course",8,80,184,44,"Course","course_id; owner_professor_id",fill=GREY,rounded=False)
    d.box("member",260,80,184,44,"Membership","account_id; course_id; role",fill=GREY,rounded=False)
    d.line([(192,102),(260,102)],arrow=False);d.label(205,95,"1");d.label(246,95,"0..*")
    d.box("release",8,152,184,52,"Release","release_id; course_id; status\nprofile / source version binding",fill=BLUE,rounded=False)
    d.box("bound",260,152,184,52,"Authorized snapshot","Policy; approved source chunks;\napplicable teaching profile",fill=BLUE,rounded=False)
    d.line([(100,124),(100,152)],arrow=False);d.label(91,135,"1");d.label(85,149,"0..*")
    d.line([(192,178),(260,178)],arrow=False);d.label(226,171,"binds")
    d.box("convo",8,232,184,52,"Conversation","conversation_id; student_id;\ncourse_id; release_id",fill=GREY,rounded=False)
    d.box("message",260,232,184,52,"Message + citations","message_id; request identity;\nsource version and locator",fill=GREY,rounded=False)
    d.line([(100,204),(100,232)],arrow=False);d.label(91,215,"1");d.label(85,229,"0..*")
    d.line([(192,258),(260,258)],arrow=False);d.label(205,251,"1");d.label(246,251,"0..*")
    d.text(8,306,"B  Derived evidence and autonomous work",10.4,True)
    d.box("evidence",8,326,184,58,"Committed learner evidence","Student + course/release scope;\nrevision; concept assessment",fill=BLUE,rounded=False)
    d.box("goal",260,326,184,58,"Goal","Approved objective; status;\nattempt limit; expiry",fill=TEAL,rounded=False)
    d.line([(352,284),(352,295),(450,295),(450,318),(100,318),(100,326)],dashed=True)
    d.connect("evidence","goal","R","L",dashed=True);d.label(226,348,"assess")
    d.box("outcome",8,412,184,52,"Plan / action / outcome","Opportunity and action IDs;\ndelivery key; recorded reason",fill=GREY,rounded=False)
    d.box("opp",260,412,184,52,"Opportunity","Event; due window; lease;\noptional goal reference",fill=GREY,rounded=False)
    d.line([(352,384),(352,412)],arrow=False);d.label(335,395,"0..1");d.label(335,409,"0..*")
    d.connect("opp","outcome","L","R");d.label(226,431,"process")
    d.finish()


def goal_states():
    d=Diagram("course-twin-goal-states",485,"Autonomous goal | State machine",
              "Four persisted statuses. Each transition names its event, guard and committed effect.")
    d.dot(226,59);d.line([(226,63),(226,109)])
    d.label(226,89,"create goal / bind approved objective")
    d.box("active",139,109,174,70,"ACTIVE", "attempt_count; attempt_limit\nexpires_at",fill=BLUE)
    d.line([(313,129),(439,129),(439,204),(258,204),(258,179)])
    d.label(346,194,"delivery / increment attempts")
    d.line([(139,143),(76,143),(76,351)])
    d.line([(207,179),(207,226),(226,226),(226,351)])
    d.line([(313,159),(449,159),(449,237),(376,237),(376,351)])
    for x,event,guards,effect in [
        (76,"accepted turn",["[all target concepts", "satisfy Equation (2)]"],"cancel pending goal work"),
        (226,"expiry sweep",["[now >= expires_at]", "expire opportunities;"],"cancel pending wake-ups"),
        (376,"cancel or revoke scope",["[active goal]", "retain goal record;"],"cancel pending goal work")]:
        d.label(x,258,event)
        d.label(x,280,guards[0])
        if x == 76:
            d.label(x,295,guards[1]);d.label(x,328,"/ "+effect)
        elif x == 226:
            d.label(x,310,"/ expire opportunities;");d.label(x,328,"cancel pending wake-ups")
        else:
            d.label(x,310,"/ cancel pending work;");d.label(x,328,"retain goal record")
    d.box("complete",8,351,136,52,"COMPLETED","Evidence threshold met",fill=TEAL)
    d.box("expire",158,351,136,52,"EXPIRED","Default expiry: 7 days",fill=GREY)
    d.box("cancel",308,351,136,52,"CANCELLED","Instructor cancellation /\nrevoked authority",fill=RED)
    d.box("limit",8,425,436,54,"Delivery limit",
          "At three deliveries, further jobs are blocked; the goal remains ACTIVE.\nA later qualifying answer can still complete it before expiry.",fill=AMBER)
    d.finish()


if __name__=="__main__":
    lifecycle()
    architecture()
    sequence("course-twin-tutoring-sequence")
    learner()
    planner()
    autonomy()
    goal_states()
    failure()
    simulation()
    sequence("course-twin-publication-sequence",publication=True)
    data()
    (OUT/"sdlc-figure-manifest.json").write_text(json.dumps(AUDIT,indent=2)+"\n")
    print(f"Built {len(AUDIT)} vector figures; minimum declared type size 9.8 pt.")
