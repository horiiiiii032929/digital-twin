import fs from 'node:fs/promises';
import {Presentation,PresentationFile} from '/Users/hikaru/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const build=process.cwd()+'/reports/generated/cto-title-build';await fs.mkdir(build,{recursive:true});
const p=Presentation.create({slideSize:{width:1280,height:720}}),s=p.slides.add();s.background.fill='#FFFFFF';
function text(value,x,y,w,h,size,bold=false,color='#172B45'){
 const t=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});t.text=value;t.text.style={typeface:'Arial',fontSize:size,bold,color,autoFit:'none'};
}
text('Course Digital Twin',82,198,1116,88,54,true);
text('Design and Evaluation of a Course Learning Assistant',85,310,1110,65,29);
text('Hikaru Rawin Horinouchi',85,483,1110,55,27,false,'#36536E');
await (await PresentationFile.exportPptx(p)).save(build+'/cover.pptx');
const png=await p.export({slide:s,format:'png',scale:1});await fs.writeFile(build+'/cover.png',new Uint8Array(await png.arrayBuffer()));
