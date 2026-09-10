import fs from 'node:fs/promises';
import path from 'node:path';
import { Presentation, PresentationFile } from '/Users/hikaru/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const root=process.cwd(), build=path.join(root,'reports/generated/cto-refined-build');
const data=JSON.parse(await fs.readFile(path.join(build,'deck-content.json'),'utf8'));
const p=Presentation.create({slideSize:{width:1280,height:720}});
function text(s,str,x,y,w,h,size=25,bold=false,color='#172B45') {
 const t=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 t.text=str;t.text.style={typeface:'Arial',fontSize:size,bold,color,autoFit:'none'};return t;
}
async function picture(s,file,box,alt) {s.images.add({blob:new Uint8Array(await fs.readFile(path.join(root,file))),contentType:'image/png',alt,fit:'contain',position:box});}
function table(s,rows,widths,y,h,compact=false,x=60,w=1160) {
 const t=s.tables.add({rows:rows.length,columns:rows[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values:rows});
 t.borders.assign({style:'solid',fill:'#D1D7DF',width:1});
 for(let r=0;r<rows.length;r++)for(let c=0;c<rows[0].length;c++){
  const cell=t.getCell(r,c);cell.fill=r===0?'#E8EDF3':r%2===0?'#F4F7FA':'#FFFFFF';
  cell.text.style={typeface:'Arial',fontSize:compact?20:23,bold:r===0,color:'#182C43'};
 }
 return t;
}

function rect(s,x,y,w,h,fill='#EDF3F8') {return s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:'none',width:0}});}
function heading(s,d){text(s,d.title,60,40,1160,60,35,true);if(d.intro)text(s,d.intro,60,116,1160,66,24);}
function conclusion(s,d){rect(s,60,579,1160,68,'#EDF3F8');rect(s,60,579,5,68,'#285E8E');text(s,d.takeaway,77,580,1123,64,25,true);if(d.limit)text(s,d.limit,60,654,1150,44,18,false,'#384D64');}
async function custom(s,d){
 const k=d.kind;
 if(!['agenda','requirements','completeness','utility','proxy','models','trial','experiment','development'].includes(k))return false;
 heading(s,k==='completeness'?{...d,intro:''}:d);
 if(k==='agenda'){
  d.rows.slice(1).forEach((r,i)=>{const y=190+i*61;rect(s,60,y,46,43,'#285E8E');text(s,String(i+1),72,y+4,34,37,27,true,'#FFFFFF');text(s,r[0].split(' · ')[1],128,y+3,365,42,26,true);text(s,r[2],520,y+3,690,42,25);if(i<5)rect(s,128,y+50,1080,1,'#DCE3EB');});
 }
 if(k==='requirements'){
  d.rows.slice(1).forEach((r,i)=>{const y=196+i*116;rect(s,60,y,1160,108,i%2?'#F4F7FA':'#EDF3F8');text(s,'R'+(i+1),78,y+15,64,45,31,true,'#285E8E');text(s,r[0].split(' · ')[1],161,y+12,360,40,27,true);text(s,r[1],161,y+44,560,58,22);text(s,'CHECK',785,y+12,410,26,15,true,'#285E8E');text(s,r[2],785,y+42,410,56,23);});
 }
 if(k==='completeness'){
  text(s,d.prompt,60,116,1160,44,27,true);
  rect(s,60,184,1160,100,'#F1F4F7');text(s,'RETRIEVED SOURCE',79,194,1110,23,15,true,'#536780');text(s,'“The stages are draft, review and publish.”',79,228,1110,47,29);
  [['Answer misses one required fact','“Draft and review.”','2 of 3 stages · Missing: publish','#FFF1E6','#98532F'],['Answer includes every required fact','“Draft, review and publish.”','3 of 3 stages · All supported','#EDF3F8','#285E8E']].forEach((v,i)=>{let x=60+i*610;rect(s,x,309,550,236,v[3]);text(s,v[0],x+20,326,510,60,25,true,v[4]);text(s,v[1],x+20,407,510,72,30);text(s,v[2],x+20,497,510,40,23,true,v[4]);});
 }
 if(k==='utility'){
  [['Rules A','0.7954'],['Guarded H','0.8002']].forEach((v,i)=>{let x=60+i*305;rect(s,x,206,280,173,i?'#EDF3F8':'#F1F4F7');text(s,v[0],x+20,222,240,43,27,true);text(s,v[1],x+20,285,240,63,43,true,'#285E8E');});
  text(s,'Small positive paired gain',60,412,585,42,27,true);text(s,'+0.004805\n95% CI: 0.003065–0.006760',60,462,585,80,25);
  rect(s,682,206,1,340,'#CED7E0');text(s,'What “utility” measures',719,214,480,42,27,true);text(s,'An authored evaluator scores the chosen action using simulated learner outcomes.',719,273,480,109,27);text(s,'Both methods obeyed 100% of tested action rules. This is a separate check from utility.',719,408,480,127,25);
 }
 if(k==='proxy'){
  [['Before delivery','0.50','n = 0 → 1 / 2'],['After one delivery','0.67','n = 1 → 2 / 3']].forEach((v,i)=>{let x=60+i*610;rect(s,x,205,550,237,i?'#FFF1E6':'#F1F4F7');text(s,v[0],x+22,225,506,45,28,true);text(s,v[1],x+22,282,506,81,58,true,i?'#98532F':'#285E8E');text(s,v[2],x+22,385,506,43,25);});
  text(s,'New assessed answers: 0 in both states',60,468,1160,44,30,true,'#98532F');text(s,'A delivered message changes the input even when the student has not demonstrated understanding.',60,521,1160,46,24);
 }
 if(k==='models'){
  const items=[['Count baseline','Count-based estimate','Uses assessed history to estimate knowledge.'],['BKT','Bayesian Knowledge Tracing','Updates the probability of knowing a concept after correct or incorrect attempts.'],['PFA','Performance Factors Analysis','Uses successes and failures to predict the probability of the next correct answer.']];
  items.forEach((v,i)=>{let x=60+i*397;rect(s,x,195,366,240,i===1?'#EDF3F8':'#F4F7FA');text(s,v[0],x+18,211,330,42,30,true,'#285E8E');text(s,v[1],x+18,263,330,65,23,true);text(s,v[2],x+18,334,330,94,23);});
  text(s,'MSE · mean squared error',60,464,550,39,25,true);text(s,'Estimate vs. simulated hidden knowledge.',60,511,550,52,23);text(s,'Brier · probability prediction error',670,464,550,39,25,true);text(s,'Next-answer probability vs. actual outcome.',670,511,550,52,23);d.limit='Both metrics average squared errors; lower is better. These simulations do not establish real-student learning gains.';
 }
 if(k==='trial'){
  [['484','tutor turns'],['654','model calls'],['16','proactive messages'],['10','synthetic replies']].forEach((v,i)=>{let x=60+i*299;rect(s,x,199,263,120,'#F1F4F7');text(s,v[0],x+16,207,235,61,43,true,'#285E8E');text(s,v[1],x+16,273,235,38,23);});
  [['Days 10–19: consent off','No proactive messages','The off-window was respected.'],['After the off-window','No resumed delivery','Sustained support was not demonstrated.']].forEach((v,i)=>{let x=60+i*610;rect(s,x,348,550,193,i?'#FFF1E6':'#EDF3F8');text(s,v[0],x+18,363,514,49,26,true);text(s,v[1],x+18,426,514,43,29,true,i?'#98532F':'#285E8E');text(s,v[2],x+18,488,514,43,23);});
 }
 if(k==='experiment'){
  [['CONTROL','Delivery-count input','The planner input rises with messages delivered.'],['CANDIDATE','Target-concept evidence','Use committed assessments relevant to this goal.']].forEach((v,i)=>{let x=60+i*610;rect(s,x,196,550,168,i?'#EDF3F8':'#F1F4F7');text(s,v[0],x+18,208,510,28,16,true,'#285E8E');text(s,v[1],x+18,250,510,43,27,true);text(s,v[2],x+18,303,510,56,23);});
  text(s,'Hold fixed',60,389,200,40,25,true);text(s,'Planner, allowed actions, retrieval and wording.',276,389,934,45,25);
  text(s,'1 · Same snapshots',60,451,550,40,25,true);text(s,'Relevant, missing, unrelated and conflicting evidence.',60,500,550,65,23);text(s,'2 · Complete histories',670,451,550,40,25,true);text(s,'Useful / missed support, inappropriate contact, authority, latency and cost.',670,500,550,65,23);
 }
 if(k==='development'){
  d.rows.slice(1).forEach((r,i)=>{let y=194+i*89;rect(s,60,y,46,44,'#285E8E');text(s,String(i+1),73,y+5,30,32,25,true,'#FFFFFF');text(s,r[0],126,y,419,74,25,true);text(s,r[1],570,y,640,76,24);if(i<3)rect(s,126,y+80,1082,1,'#DCE3EB');});
 }
 conclusion(s,d);return true;
}
for(const d of data.slides){
 const s=p.slides.add();s.background.fill='#FFFFFF';
 if(await custom(s,d)){}else if(d.kind==='cover'){
  text(s,d.title,70,105,1120,120,48,true);text(s,d.subtitle,73,241,1100,85,28);rect(s,73,375,6,192,'#285E8E');text(s,'Publish a course. Answer from its evidence.\nContinue permitted support over time.',98,391,1090,114,32,true);text(s,d.details,98,529,1050,100,22);
 }else{
  text(s,d.title,60,40,1160,62,35,true);
  if(d.kind==='roadmap'){
   text(s,d.intro,60,110,1160,60,25);
   table(s,d.rows,d.widths,187,410,false);
   text(s,d.takeaway,60,618,1160,65,24,true);
  }
  if(d.kind==='focusFigure'){
   text(s,d.intro,60,110,1160,60,24);
   await picture(s,d.image,{left:60,top:173,width:1160,height:397},d.title);
   conclusion(s,{...d,limit:''});
  }
  if(d.kind==='screenPair'){
   text(s,d.intro,60,112,1160,64,24);
   for(let i=0;i<2;i++){
    const x=60+610*i;
    text(s,d.labels[i],x,190,550,40,27,true);
    await picture(s,d.images[i],{left:x,top:245,width:550,height:294},d.labels[i]);
    text(s,d.captions[i],x,550,550,35,23);
   }
   text(s,d.takeaway,60,592,1160,56,25,true);
  }
  if(d.kind==='teachingExample'){
   text(s,d.intro,60,110,1160,60,24);
   text(s,d.labels[0],60,200,550,45,27,true);
   text(s,d.left,60,270,530,240,29);
   text(s,d.labels[1],670,200,550,45,27,true);
   text(s,d.quote,670,270,550,240,29);
   text(s,d.takeaway,60,580,1160,70,27,true);
  }
  if(d.kind==='metricExample'){
   text(s,d.intro,60,110,1160,65,24);
   d.items.forEach(([label,body],i)=>{
    const x=60+i*610;
    text(s,label,x,200,550,70,27,true);
    text(s,body,x,285,550,105,27);
    text(s,d.examples[i],x,425,550,110,25);
   });
   text(s,d.takeaway,60,588,1160,62,27,true);
  }
  if(d.kind==='semanticExample'){
   text(s,d.intro,60,110,1160,65,24);
   text(s,'Source requirement',60,210,610,42,28,true);
   text(s,'Exactly two seals are required.',60,270,610,90,30);
   text(s,'Meaning added by the revision',60,380,610,42,28,true);
   text(s,'Two seals guarantee acceptance.',60,440,610,90,30,true,'#9B4E38');
   table(s,d.rows,[300,200],210,300,true,720,500);
   text(s,d.takeaway,60,573,1160,70,27,true);
  }
  if(d.kind==='figure') {
   if(d.diagramCaption) text(s,d.diagramCaption,60,107,1160,66,23);
   await picture(s,d.image,{left:40,top:d.diagramCaption?177:98,width:1200,height:d.diagramCaption?450:530},d.title);
  }
  if(d.kind==='explanation'){
   text(s,d.intro,60,112,1160,75,25);
   d.items.forEach(([heading,body],i)=>{
    const x=60+i*610;
    rect(s,x,200,550,349,i?'#FFF1E6':'#F1F4F7');
    text(s,heading,x+18,213,550,70,28,true);
    text(s,body,x+18,294,514,240,25);
   });
   conclusion(s,{...d,limit:''});
   if(d.limit) text(s,d.limit,60,651,1150,45,18,false,'#384D64');
  }
  if(d.kind==='readerTable'){
   text(s,d.intro,60,110,1160,70,24);
   const h=Math.min(350,Math.max(230,d.rows.length*68));
   const nt=table(s,d.rows,d.widths,195,h,false);
   if(d.number===17)for(let c=0;c<3;c++){nt.getCell(4,c).fill='#E4EEF7';nt.getCell(4,c).text.style={typeface:'Arial',fontSize:23,bold:true,color:'#182C43'};}
   if(d.number===29){nt.getCell(3,2).fill='#FFF1E6';nt.getCell(3,2).text.style={typeface:'Arial',fontSize:23,bold:true,color:'#182C43'};}
   conclusion(s,{...d,limit:''});
   if(d.limit)text(s,d.limit,60,651,1150,45,18,false,'#384D64');
  }
  if(d.kind==='panels'){
   if(d.intro)text(s,d.intro,60,112,1160,64,24);
   const n=d.items.length,w=(1160-(n-1)*42)/n;
   d.items.forEach(([label,body],i)=>{
    const x=60+i*(w+42);
    text(s,label,x,210,w,70,28,true);
    text(s,body,x,290,w,245,n===3?25:27);
   });
   text(s,d.takeaway,60,572,1160,78,28,true);
  }
  if(d.kind==='results'){
   text(s,d.intro,60,112,1160,65,24);
   d.evidence.forEach(([label,value],i)=>{
    text(s,label,60,215+i*82,270,65,26,true);
    text(s,value,355,215+i*82,865,65,27);
   });
   text(s,d.takeaway,60,585,1160,70,27,true);
  }
  if(d.kind==='termComparison'){
   text(s,d.intro,60,112,1160,64,24);
   text(s,'Knowledge estimate',60,185,550,40,27,true);
   text(s,'Contact timing',670,185,550,40,27,true);
   for(const [entries,x] of [[d.items,60],[d.policies,670]])entries.forEach(([label,body],i)=>{
    text(s,label,x,235+i*105,550,34,24,true);
    text(s,body,x,274+i*105,550,72,22);
   });
   text(s,d.takeaway,60,580,1160,65,27,true);
  }
  if(d.kind==='glossary')table(s,[['Term','Full name / meaning','How to read it here'],...d.rows],[170,325,665],125,490,true);
  if(d.kind==='example'){
   text(s,d.prompt,60,125,1160,45,27,true);
   text(s,d.source,60,185,1160,70,28);
   text(s,'INCOMPLETE',60,300,540,40,22,true,'#9B4E38');
   text(s,d.bad,60,360,540,70,33);
   text(s,'COMPLETE',670,300,540,40,22,true,'#285E8E');
   text(s,d.good,670,360,540,70,33);
   text(s,'Missing required item: publish',60,450,550,50,25);
   text(s,d.takeaway,60,565,1160,85,28,true);
  }
  if(d.kind==='charts'){
   text(s,d.intro,60,110,1160,63,23);
   const dual=d.charts.length===2, w=dual?550:(d.side?770:1160);
   d.charts.forEach((c,i)=>{
    const x=60+i*610;
    text(s,c.title,x,188,w,42,25,true);
    s.charts.add('bar',{
     position:{left:x,top:235,width:w,height:dual?285:310},
     categories:c.categories,series:c.series.map(v=>({...v,valuesFormatCode:c.format,dataLabelOverrides:v.values.some(val=>val===0)?v.values.map((val,idx)=>({idx,showValue:val!==0,showSeriesName:false,showCategoryName:false,position:c.stacked?'center':'outEnd',textStyle:{typeface:'Arial',fontSize:22,bold:true,fill:c.stacked?'#FFFFFF':'#172B45'}})):[]})),
     barOptions:{direction:'column',grouping:c.stacked?'stacked':'clustered',gapWidth:90},
     hasLegend:c.series.length>1,
     legend:{position:'bottom',textStyle:{typeface:'Arial',fontSize:19,fill:'#172B45'}},
     xAxis:{textStyle:{typeface:'Arial',fontSize:20,fill:'#172B45'},majorGridlines:null},
     yAxis:{min:0,max:c.max,numberFormatCode:c.axisFormat||c.format,textStyle:{typeface:'Arial',fontSize:18,fill:'#4B5563'},majorGridlines:{fill:'#E0E5EB',width:1}},
     dataLabels:{showValue:true,position:c.stacked?'center':'outEnd',textStyle:{typeface:'Arial',fontSize:22,bold:true,fill:c.stacked?'#FFFFFF':'#172B45'}},
     chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'
    });
    if(c.detail)text(s,c.detail,x,527,w,46,20);
   });
   if(d.side)d.side.forEach(([label,body],i)=>{
    text(s,label,875,228+i*170,345,65,27,true,'#285E8E');
    text(s,body,875,298+i*170,345,106,22);
   });
   conclusion(s,{...d,limit:''});
  }
  if(d.kind==='video') {
   text(s,d.videoGuide,60,100,1160,40,24);
   await picture(s,d.image,{left:190,top:140,width:900,height:506.25},'EMBEDDED_DEMO_VIDEO_POSTER');
  }
  if(d.kind==='table'){
   const y=d.intro?158:125;
   if(d.intro)text(s,d.intro,60,99,1160,53,22,false);
   const h=d.compact?430:Math.min(d.points?(d.intro?280:310):(d.intro?390:430),Math.max(220,d.rows.length*60));
   table(s,d.rows,d.widths,y,h,d.compact);
   (d.points||[]).forEach((v,i)=>text(s,v,65,y+h+20+i*38,1145,40,23,i===0));
  }
  if(d.kind==='settings'){
   table(s,d.rows,[280,420],130,330,false,60,700);
   text(s,'Saved response',800,130,400,40,25,true);
   text(s,'“'+d.quote+'”',800,190,400,210,28);
   d.points.forEach((v,i)=>text(s,v,65,485+i*43,1140,42,25,i===1));
  }
  if(d.kind==='wording'){
   table(s,d.rows,[340,220],130,310,false,60,560);
   d.points.forEach((v,i)=>text(s,v,670,135+i*115,545,110,26,i===2));
   text(s,d.decision,65,510,1140,55,28,true);
  }
  if(d.kind==='closing'||d.kind==='questions')d.sections.forEach(([label,body],i)=>{
   text(s,label,65,145+i*155,260,55,28,true);text(s,body,345,145+i*155,855,120,28);
  });
 }
 if(d.gloss) d.gloss.forEach((v,i)=>text(s,v,60,590+i*23,1150,24,17,false,'#384D64'));
 if(d.termNote)text(s,d.termNote,60,651,1150,45,17,false,'#384D64');
 else if(d.foot)text(s,d.foot,60,651,1150,47,18,false,'#4B5563');
 text(s,d.chapter,60,8,970,20,15,false,'#285E8E');
 text(s,String(d.number)+' / '+data.slides.length,1130,700,100,18,12,false,'#687384');
 s.speakerNotes.textFrame.setText(d.notes+'\n\nSources\n'+d.sources.join('\n'));
}
await (await PresentationFile.exportPptx(p)).save(path.join(build,'candidate-base.pptx'));
await fs.mkdir(path.join(build,'renders'),{recursive:true});
for(let i=0;i<data.slides.length;i++){
 const slide=p.slides.items[i];
 const png=await p.export({slide,format:'png',scale:1});
 await fs.writeFile(path.join(build,'renders',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
console.log('Exported '+data.slides.length+' slides');
