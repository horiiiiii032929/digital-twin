"""Build editable draw.io presentation diagrams. Export with draw.io Desktop.
Run: uv run python -m scripts.build_presentation_diagrams
"""
from pathlib import Path
import argparse
import subprocess
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/presentation/diagrams"
INK="#172438"; MUTED="#536174"; BLUE="#2859AA"; TEAL="#14796D"; RED="#AA403B"
class Page:
    def __init__(self, name, title, subtitle):
        self.diagram=E.Element("diagram", id=name, name=name)
        model=E.SubElement(self.diagram,"mxGraphModel",dx="1600",dy="900",grid="1",gridSize="10",
            page="1",pageScale="1",pageWidth="1600",pageHeight="900",background="#ffffff",math="0",shadow="0")
        self.root=E.SubElement(model,"root")
        E.SubElement(self.root,"mxCell",id="0")
        E.SubElement(self.root,"mxCell",id="1",parent="0")
        self.n=0
        self.nodes={}
        self.box(0,0,1600,900,"",fill="#FFFFFF",stroke="none")
        self.text(60,36,1480,55,title,40,INK,True)
        self.text(60,98,1480,45,subtitle,23,MUTED)
    def box(self,x,y,w,h,value,fill="#F3F6FA",stroke="#C5CFDA",size=25,bold=False):
        self.n+=1; ident=f"v{self.n}"
        cell=E.SubElement(self.root,"mxCell",id=ident,value=value,vertex="1",parent="1",
            style=f"rounded=0;whiteSpace=wrap;html=0;align=center;verticalAlign=middle;spacing=14;fontFamily=Arial;fontSize={size};fontColor={INK};fontStyle={1 if bold else 0};fillColor={fill};strokeColor={stroke};strokeWidth=2;")
        E.SubElement(cell,"mxGeometry",x=str(x),y=str(y),width=str(w),height=str(h),attrib={"as":"geometry"})
        self.nodes[ident]=(x,y,w,h)
        return ident
    def text(self,x,y,w,h,value,size=23,color=INK,bold=False):
        ident=self.box(x,y,w,h,value,"none","none",size,bold)
        self.nodes.pop(ident)
        cell=self.root[-1]; cell.set("style",cell.get("style")+f"align=left;spacing=0;fontColor={color};")
        return ident
    def arrow(self,x1,y1,x2,y2,color=MUTED,dashed=False,points=()):
        self.n+=1
        cell=E.SubElement(self.root,"mxCell",id=f"e{self.n}",edge="1",parent="1",
            style=f"edgeStyle=none;rounded=0;html=0;endArrow=block;endFill=1;strokeColor={color};strokeWidth=2;dashed={1 if dashed else 0};")
        for end, px, py in [("source",x1,y1),("target",x2,y2)]:
            for ident,(x,y,w,h) in reversed(self.nodes.items()):
                if w>=1600: continue
                on_edge=(abs(px-x)<1 or abs(px-x-w)<1 or abs(py-y)<1 or abs(py-y-h)<1)
                if on_edge and x<=px<=x+w and y<=py<=y+h:
                    cell.set(end,ident)
                    prefix="exit" if end=="source" else "entry"
                    cell.set("style",cell.get("style")+f"{prefix}X={(px-x)/w};{prefix}Y={(py-y)/h};{prefix}Dx=0;{prefix}Dy=0;")
                    break
        geo=E.SubElement(cell,"mxGeometry",relative="1",attrib={"as":"geometry"})
        E.SubElement(geo,"mxPoint",x=str(x1),y=str(y1),attrib={"as":"sourcePoint"})
        E.SubElement(geo,"mxPoint",x=str(x2),y=str(y2),attrib={"as":"targetPoint"})
        if points:
            array=E.SubElement(geo,"Array",attrib={"as":"points"})
            for x,y in points: E.SubElement(array,"mxPoint",x=str(x),y=str(y))
    def footer(self,value):
        self.text(60,830,1480,44,value,20,MUTED)

pages=[]
p=Page("01-system-boundaries","System boundaries and comparison points",
       "Logical service view · The application owns authority, evidence and saved effects")
p.box(60,195,260,100,"Professor workspace\nSetup and review",fill="#EAF0FC",stroke=BLUE)
p.box(60,360,260,100,"Student workspace\nCourse conversation",fill="#EAF0FC",stroke=BLUE)
p.box(60,540,260,100,"Worker entry point\nDue opportunities",fill="#E7F4F0",stroke=TEAL)
p.box(385,195,275,100,"Publication services\nApproved release")
p.box(385,360,275,100,"Tutoring services\nScope and evidence")
p.box(385,540,275,100,"Autonomy services\nEligibility and delivery")
for y in [245,410,590]: p.arrow(320,y,385,y)
p.box(740,180,800,500,"",fill="#FFFFFF")
p.text(765,198,740,38,"Compared components inside these boundaries",25,INK,True)
p.box(785,265,325,100,"Evidence selection\nLexical / typed targets",fill="#EAF0FC",stroke=BLUE)
p.box(1170,265,325,100,"Action planner\nA / B / C / C+V / H",fill="#EAF0FC",stroke=BLUE)
p.box(785,425,325,100,"Planner-state adapter\nDelivery / event proxy",fill="#FFF5E5",stroke="#B17B26")
p.box(1170,425,325,100,"Instruction wording\nSource / typed / revised",fill="#EAF0FC",stroke=BLUE)
p.text(785,565,705,76,"BKT/PFA were experimental alternatives.\nThey do not drive the default planner adapter.",24,RED)
p.arrow(660,410,740,410)
p.arrow(660,590,740,590)
p.box(385,715,1155,78,"Repository interfaces: releases · turns and learner records · jobs and delivery identity",
      fill="#E7F4F0",stroke=TEAL,size=25)
p.arrow(522,295,385,754,points=[(700,295),(700,690),(355,690),(355,754)])
p.arrow(1140,680,1140,715)
p.footer("Source: report architecture + learner-decision detail; comparison map: presentation design-comparisons.md")
pages.append(p)

p=Page("02-factual-designs","Three factual paths and their failure point",
       "Round 1 · Same 495 development cases · Deterministic extraction · No external model calls")
rows=[
(205,"Lexical / any-hit","Lexical retrieval","Accept any hit","Extractive response","52.66%","100.00%"),
(375,"Evidence-first\nhierarchical","Hierarchical\nretrieval","Whole-question\ncoverage","Answer or abstain","24.81%","36.46%"),
(545,"Plan-observe /\nevent-sourced","Split question\nRetrieve + merge","Hierarchy +\nwhole-question check","Answer or abstain","24.81%","36.20%")]
p.text(1265,152,130,45,"Grounded",21,MUTED,True)
p.text(1400,145,150,58,"Answerable\naction",21,MUTED,True)
for y,label,a,b,c,g,ans in rows:
    p.text(60,y,270,100,label,26,INK,True)
    p.box(355,y,250,100,a,size=24)
    p.box(660,y,290,100,b,fill="#FCEDEB" if y>205 else "#F3F6FA",stroke=RED if y>205 else "#C5CFDA",size=24)
    p.box(1005,y,215,100,c,size=24)
    p.arrow(605,y+50,660,y+50);p.arrow(950,y+50,1005,y+50)
    p.text(1270,y+25,120,50,g,30,BLUE,True)
    p.text(1410,y+25,140,50,ans,30,INK,True)
p.box(60,700,1480,90,"Shared failure: question scaffolding became required evidence → excess abstention.\nThe control still selected incomplete or incorrect source regions.",fill="#FFF5E5",stroke="#B17B26",size=26)
p.footer("No candidate passed the quality gates. This factual-path result does not reject hierarchy or event sourcing in general.")
pages.append(p)

p=Page("03-planner-designs","Planner designs: added stages and retained fallback",
       "Shared inputs: event, state card and permitted actions · Shared authority and evidence controls remain outside")
p.text(60,178,255,42,"Design",23,MUTED,True)
p.text(355,178,805,42,"Decision path",23,MUTED,True)
p.text(1225,178,325,42,"Interpretation",23,MUTED,True)
for y,name,steps,comment in [
(235,"A · Event rule",["Deterministic rule","Baseline action"],"Retained as fallback"),
(345,"B · Model planner",["Model proposal","Permitted action"],"No lookahead"),
(455,"C · Lookahead",["Model proposal","Analytic ranking","Selected action"],"More stages did not\nguarantee better utility"),
(565,"C+V · Verifier",["Same C selection","Reject-only verifier","Action / no action"],"Rejection supplies\nno alternative action")]:
    p.text(60,y,260,75,name,25,INK,True)
    widths= [360,360] if len(steps)==2 else [230,250,230]
    x=355
    for i,(step,w) in enumerate(zip(steps,widths)):
        p.box(x,y,w,75,step,size=23)
        if i<len(steps)-1:p.arrow(x+w,y+37,x+w+35,y+37)
        x+=w+35
    p.text(1225,y,325,80,comment,23,MUTED)
p.text(60,695,260,95,"H · Guarded\nreplacement",25,TEAL,True)
p.box(355,685,805,105,"Keep A unless the proposal is valid, analytically best,\nand improves fallback utility by at least 0.04.",
      fill="#E7F4F0",stroke=TEAL,size=25)
p.text(1225,685,325,105,"No authorized evidence\n→ no action",24,RED,True)
p.footer("Structure: comparison build + Fold 003 audit + report planner rules. Model-specific added value remains unisolated.")
pages.append(p)

p=Page("04-learner-input-gap","Saved assessment and planner input use different paths",
       "Reported default implementation · Evidence confidence, planning proxies and mastery are different quantities")
p.box(60,175,1480,75,"Saved activity: committed student observations and delivered goal actions",fill="#EAF0FC",stroke=BLUE,size=28)
p.arrow(420,250,420,315);p.arrow(1170,250,1170,315)
p.box(60,315,715,100,"Assessment evidence\nTarget concept + outcome + source + course/release",size=25)
p.box(835,315,705,100,"Default job-snapshot adapter\nDelivered actions d + supporting observation IDs k",fill="#FFF5E5",stroke="#B17B26",size=25)
p.arrow(420,415,420,465);p.arrow(1170,415,1170,465)
p.box(60,465,715,120,"Goal completion\nExact objective; every target concept needs:\n≥ 2 correct, 0 incorrect, confidence ≥ 0.5",fill="#E7F4F0",stroke=TEAL,size=25)
p.box(835,465,705,120,"Planner proxy: p = min(0.95, (d + 1) / (d + 2))\n0 deliveries: 0.50  |  1 delivery: 0.67\nThis can rise without a student answer.",fill="#FCEDEB",stroke=RED,size=25)
p.text(60,620,715,100,"Confidence = min(0.95, a / (a + 2)).\nTwo assessed attempts give 0.5, even if incorrect.\nOutcome counts must therefore be checked too.",23,MUTED)
p.text(835,620,705,100,"Uncertainty = 1 / (k + 1).\nElapsed observation time is not populated.\nBKT/PFA are not connected to this adapter.",23,MUTED)
p.box(60,750,1480,62,"Next comparison (not yet run): replace only the adapter with committed target-concept evidence.",
      fill="#FFFFFF",stroke=BLUE,size=24)
p.footer("Source: report learner-decision-detail, assessment and planner-proxy equations. Completed goals do not establish learning gains.")
pages.append(p)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export',action='store_true',help='Also export PNG, SVG and a review PDF with draw.io Desktop')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    mx=E.Element("mxfile",host="app.diagrams.net",agent="Codex",version="30.0.4")
    for page in pages:
        # Some arrows precede their destination box in the drawing order.
        # Bind them after every native vertex exists.
        for cell in page.root.findall('mxCell'):
            if cell.get('edge')!='1': continue
            geo=cell.find('mxGeometry')
            for end in ['source','target']:
                point=geo.find(f"mxPoint[@as='{end}Point']")
                px,py=float(point.get('x')),float(point.get('y'))
                for ident,(x,y,w,h) in reversed(page.nodes.items()):
                    if w>=1600: continue
                    on_edge=any(abs(v)<1 for v in [px-x,px-x-w,py-y,py-y-h])
                    if on_edge and x<=px<=x+w and y<=py<=y+h:
                        cell.set(end,ident)
                        prefix='exit' if end=='source' else 'entry'
                        cell.set('style',cell.get('style')+f'{prefix}X={(px-x)/w};{prefix}Y={(py-y)/h};{prefix}Dx=0;{prefix}Dy=0;')
                        break
        mx.append(page.diagram)
    E.indent(mx)
    E.ElementTree(mx).write(OUT/"presentation-diagrams.drawio",encoding="utf-8",xml_declaration=True)
    print(OUT/"presentation-diagrams.drawio")
    if args.export:
        app='/Applications/draw.io.app/Contents/MacOS/draw.io'
        source=str(OUT/'presentation-diagrams.drawio')
        for index,page in enumerate(pages,1):
            for fmt in ['png','svg']:
                subprocess.run([app,'--export','--format',fmt,'--page-index',str(index),
                    '--scale','1.5','--embed-diagram','--output',str(OUT/f'{page.diagram.get("id")}.{fmt}'),source],check=True)
        subprocess.run([app,'--export','--format','pdf','--all-pages','--output',str(OUT/'presentation-diagrams.pdf'),source],check=True)
if __name__=="__main__":main()
