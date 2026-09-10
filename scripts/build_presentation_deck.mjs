import fs from 'node:fs/promises';
import path from 'node:path';
import { Presentation, PresentationFile } from '/Users/hikaru/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const root=process.cwd(), build=path.join(root,'reports/generated/slide-build');
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
  const cell=t.getCell(r,c);cell.fill=r===0?'#E8EDF3':'#FFFFFF';
  cell.text.style={typeface:'Arial',fontSize:compact?20:23,bold:r===0,color:'#182C43'};
 }
 return t;
}
for(const d of data.slides){
 const s=p.slides.add();s.background.fill='#FFFFFF';
 if(d.kind==='cover'){
  text(s,d.title,70,150,1140,160,50,true);text(s,d.subtitle,73,337,1100,80,28);text(s,d.details,73,500,800,130,24);
 }else{
  text(s,d.title,60,30,1160,70,35,true);
  if(d.kind==='focusFigure'){
   text(s,d.intro,60,110,1160,60,24);
   await picture(s,d.image,{left:60,top:173,width:1160,height:397},d.title);
   text(s,d.takeaway,60,587,1160,65,27,true);
  }
  if(d.kind==='screenPair'){
   text(s,d.intro,60,112,1160,64,24);
   for(let i=0;i<2;i++){
    const x=60+610*i;
    text(s,d.labels[i],x,190,550,40,27,true);
    await picture(s,d.images[i],{left:x,top:245,width:550,height:294},d.labels[i]);
    text(s,d.captions[i],x,550,550,35,23);
   }
   text(s,d.takeaway,60,604,1160,45,27,true);
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
  if(d.kind==='figure') await picture(s,d.image,{left:40,top:98,width:1200,height:550},d.title);
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
     yAxis:{min:0,max:c.max,numberFormatCode:c.format,textStyle:{typeface:'Arial',fontSize:18,fill:'#4B5563'},majorGridlines:{fill:'#E0E5EB',width:1}},
     dataLabels:{showValue:true,position:c.stacked?'center':'outEnd',textStyle:{typeface:'Arial',fontSize:22,bold:true,fill:c.stacked?'#FFFFFF':'#172B45'}},
     chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'
    });
    if(c.detail)text(s,c.detail,x,527,w,49,20);
   });
   if(d.side)d.side.forEach(([label,body],i)=>{
    text(s,label,875,240+i*158,345,70,29,true);
    text(s,body,875,309+i*158,345,90,23);
   });
   text(s,d.takeaway,60,590,1160,64,26,true);
  }
  if(d.kind==='video') await picture(s,d.image,{left:160,top:112,width:960,height:540},'EMBEDDED_DEMO_VIDEO_POSTER');
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
 else if(d.foot)text(s,d.foot,60,665,1135,34,14,false,'#4B5563');
 text(s,(d.backup?'Backup · ':'')+d.number,1130,700,100,18,12,false,'#687384');
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
