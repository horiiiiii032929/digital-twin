"""Refine diagram hierarchy and routing, preserving draw.io sources and notation."""
from pathlib import Path
import xml.etree.ElementTree as E
import subprocess,sys
SRC=Path('reports/presentation/diagrams/cto');OUT=Path('reports/presentation/diagrams/cto-refined');OUT.mkdir(parents=True,exist_ok=True)
used=['01-context','02-containers','03-erd','06-answer-path','07-answer-alternatives','08-guarded-planner','09-goal-states','10-authority-change','11-retry','12-execution']
for name in used:
 if len(sys.argv)>1 and name not in sys.argv[1:]:continue
 tree=E.parse(SRC/(name+'.drawio'));cells=tree.findall('.//mxCell');byid={c.get('id'):c for c in cells}
 for c in cells:
  st=c.get('style','');v=c.get('value','')
  if c.get('vertex')=='1':
   g=c.find('mxGeometry');w=float(g.get('width','0'));h=float(g.get('height','0'))
   if w>50 and h>45:
    st+='strokeWidth=1.8;'
    if 'Software system' in v or 'baseline action A' in v or v=='Use baseline A':st+='fillColor=#EAF1F8;strokeColor=#285E8E;fontStyle=1;'
    elif 'Data store' in v or 'Saved state' in v:st+='fillColor=#F1F4F7;'
    elif 'whole-question coverage' in v:st+='fillColor=#FFF1E6;strokeColor=#A86125;fontStyle=1;'
    elif v.startswith('Completed') or 'save response' in v:st+='fillColor=#EAF1F8;'
    elif 'shape=note' in st:st+='fillColor=#F7F9FB;strokeColor=#B2C0CD;'
    elif '[Person]' in v:st+='fillColor=#F1F4F7;'
   c.set('style',st)
  elif c.get('edge')=='1':c.set('style',st+'strokeWidth=1.6;')
 if name=='03-erd':
  # Planar layout of account/release -> goal/conversation; no crossing or shared junctions.
  placements={'Account':(440,0,350,170),'Published release':(440,475,350,180),'Learning goal':(0,235,350,215),'Conversation':(850,235,370,185),'Learner observation':(1290,0,370,190),'Concept assessment':(1290,455,370,220)}
  for c in cells:
   v=c.get('value','');title=v.split('\n')[0]
   if title in placements:
    x,y,w,h=placements[title];g=c.find('mxGeometry')
    for k,val in dict(x=x,y=y,width=w,height=h).items():g.set(k,str(val))
    c.set('style',c.get('style','')+'fontSize=29;fillColor='+('#EAF1F8' if title in ['Learning goal','Concept assessment'] else '#FFFFFF')+';')
  for c in cells:
   if c.get('edge')!='1':continue
   av=byid[c.get('source')].get('value','').split('\n')[0];bv=byid[c.get('target')].get('value','').split('\n')[0]
   g=c.find('mxGeometry')
   for child in list(g):g.remove(child)
   anchor={('Account','Learning goal'):'exitX=0;exitY=0.5;entryX=0.5;entryY=0;',('Account','Conversation'):'exitX=1;exitY=0.5;entryX=0.5;entryY=0;',('Published release','Learning goal'):'exitX=0;exitY=0.5;entryX=0.5;entryY=1;',('Published release','Conversation'):'exitX=1;exitY=0.5;entryX=0.5;entryY=1;',('Conversation','Learner observation'):'exitX=1;exitY=0.3;entryX=0.5;entryY=1;',('Conversation','Concept assessment'):'exitX=1;exitY=0.7;entryX=0.5;entryY=0;'}[(av,bv)]
   c.set('style','edgeStyle=orthogonalEdgeStyle;rounded=0;startArrow=ERmandOne;startFill=0;endArrow=ERzeroToMany;endFill=0;strokeColor=#31516E;strokeWidth=2;'+anchor)
 if name=='02-containers':
  places={'2':(0,140,300,170),'3':(460,60,430,200),'4':(460,410,430,180),'5':(1110,215,320,160),'6':(0,415,300,150),'7':(1110,480,320,120)}
  for ident,vals in places.items():
   g=byid[ident].find('mxGeometry')
   for k,v in zip(['x','y','width','height'],vals):g.set(k,str(v))
  byid['5'].set('value','SQLite [Data store]\nDialogue, goals\nand jobs')
  # Route model calls above and to the right of the stores, away from read/write lines.
  routes={'8':('exitX=1;exitY=0.35;entryX=0;entryY=0.7;',[]),'9':('exitX=1;exitY=0.65;entryX=0;entryY=0.25;',[(990,190),(990,255)]),'10':('exitX=1;exitY=0.2;entryX=0;entryY=0.8;',[(1010,446),(1010,343)]),'11':('exitX=0;exitY=0.9;entryX=1;entryY=0.3;',[(370,240),(370,460)]),'12':('exitX=1;exitY=0.75;entryX=0;entryY=0.55;',[]),'13':('exitX=1;exitY=0.15;entryX=1;entryY=0.5;',[(1530,90),(1530,540)])}
  for ident,(st,pts) in routes.items():
   c=byid[ident];g=c.find('mxGeometry')
   for child in list(g):g.remove(child)
   if pts:
    arr=E.SubElement(g,'Array',{'as':'points'})
    for x,y in pts:E.SubElement(arr,'mxPoint',{'x':str(x),'y':str(y)})
   c.set('style',c.get('style','')+st)
   if ident in ['12','13']:c.set('value','model calls')
  byid['3'].set('style',byid['3'].get('style')+'fillColor=#EAF1F8;')
  byid['4'].set('style',byid['4'].get('style')+'fillColor=#EAF1F8;')
 if name=='09-goal-states':
  byid['11'].set('value','A message increments attempts.\nAn attempt limit does not\ncomplete the goal.')
  ng=byid['11'].find('mxGeometry');ng.set('x','40');ng.set('y','390');ng.set('width','440');ng.set('height','150')
  for c in cells:
   if c.get('edge')=='1' and byid[c.get('source')].get('value','').startswith('Active'):
    b=byid[c.get('target')].get('value','');c.set('style',c.get('style','')+'exitX=1;exitY='+str({'Completed':.15,'Expired':.5,'Cancelled':.85}[b])+';entryX=0;entryY=0.5;')
 if name in ['10-authority-change','11-retry','12-execution']:
  for c in cells:
   if c.get('edge')=='1' and any(w in c.get('value','').lower() for w in ['recheck','reject stale','restart','read due']):
    c.set('style',c.get('style','')+'strokeColor=#285E8E;fontColor=#285E8E;fontStyle=1;strokeWidth=2.5;')
 if name=='06-answer-path':
  for c in cells:
   if c.get('value','').startswith('Check evidence'):c.set('style',c.get('style','')+'fillColor=#EAF1F8;fontStyle=1;')
 out=OUT/(name+'.drawio');tree.write(out,encoding='utf-8',xml_declaration=True)
 subprocess.run(['/Applications/draw.io.app/Contents/MacOS/draw.io','--export','--format','png','--scale','1.5','--border','12','--output',str(out.with_suffix('.png')),str(out)],check=True,stdout=subprocess.DEVNULL)
print('Refined draw.io diagrams exported')
