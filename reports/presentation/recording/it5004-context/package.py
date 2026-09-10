"""Validate and package the three context-first demo edits without replacing prior output."""
import hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
RENDER=ROOT/'output/playwright/it5004-context'
NAMES=[('CourseSetup','course-setup','Course setup and student answer',40,'Professor settings → published course → a shopping-site question → the original lecture citation.'),('ContinuingSupport','continuing-support','Continuing student support',35,'Recorded check-in → the saved conversation → the actual goal and observation state.'),('InstructorReview','instructor-review','From student difficulty to professor review',38,'Maya’s unresolved question → class-level signals → the suggestion → the saved professor decision.')]
validation=[]
for suite,name,title,duration,desc in NAMES:
 output=HERE/(name+'.mp4')
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(RENDER/(name+'-render.mp4')),'-an','-c:v','copy','-movflags','+faststart',str(output)],check=True)
 info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]))
 v=info['streams'][0]
 assert len(info['streams'])==1 and v['codec_name']=='h264' and v['width']==1920 and v['height']==1080 and v['r_frame_rate']=='30/1'
 assert abs(float(info['format']['duration'])-duration)<.05
 subprocess.run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'],check=True)
 subprocess.run(['ffmpeg','-y','-v','error','-ss','1','-i',str(output),'-frames:v','1',str(HERE/(name+'-poster.png'))],check=True)
 validation.append(dict(file=output.name,seconds=duration,width=1920,height=1080,fps=30,codec='h264',audio_streams=0,full_decode='pass',sha256=hashlib.sha256(output.read_bytes()).hexdigest()))
(HERE/'validation.json').write_text(json.dumps(validation,indent=2))
dest=Path.home()/'Desktop/Course Digital Twin — Demo Review'
i=2
while dest.exists():
 dest=Path.home()/f'Desktop/Course Digital Twin — Demo Review {i}';i+=1
dest.mkdir()
for p in HERE.iterdir():
 if p.suffix in ['.mp4','.png','.json','.md','.tsx']:shutil.copy2(p,dest/p.name)
cards=''.join(f'<section id="demo-{i}"><div class="eyebrow">DEMO {i} · {duration} SECONDS</div><h2>{title}</h2><p>{desc}</p><video controls playsinline preload="metadata" poster="{name}-poster.png" src="{name}.mp4"></video><a download href="{name}.mp4">Download MP4</a></section>' for i,(_,name,title,duration,desc) in enumerate(NAMES,1))
html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>IT5004 — Three revised demos</title><style>*{box-sizing:border-box}body{margin:0;background:#edf0f4;color:#182f49;font-family:Arial,sans-serif}main{max-width:1240px;margin:auto;padding:40px 24px}header{padding:0 0 28px}h1{font-size:34px;margin:12px 0}p{line-height:1.5;color:#526478}nav{display:flex;gap:24px;flex-wrap:wrap}a{color:#3d4aad}section{background:white;border:1px solid #dce2e9;border-radius:14px;padding:26px;margin-bottom:30px;scroll-margin-top:20px}.eyebrow{font-size:13px;letter-spacing:.1em;font-weight:bold;color:#657389}h2{font-size:25px;margin:10px 0}video{width:100%;aspect-ratio:16/9;background:#182f49;border-radius:8px;margin:6px 0 16px}footer{color:#657389;font-size:14px}</style><main><header><div class="eyebrow">COURSE DIGITAL TWIN · IT5004</div><h1>Three revised product demos</h1><p>Full-view openings, restrained zoom and one connected shopping-site example. Total: 1 minute 53 seconds.</p><nav><a href="#demo-1">1. Course setup</a><a href="#demo-2">2. Continuing support</a><a href="#demo-3">3. Professor review</a></nav></header>'''+cards+'''<footer>Real application recordings with synthetic students and saved real-AI responses. The support sequence replays a recorded event under virtual time. <a href="README.md">Recording notes</a></footer></main><script>document.querySelectorAll('video').forEach(v=>v.addEventListener('play',()=>document.querySelectorAll('video').forEach(other=>{if(other!==v)other.pause()})))</script></html>'''
(dest/'index.html').write_text(html)
(HERE/'delivery-path.txt').write_text(str(dest))
print(dest)
