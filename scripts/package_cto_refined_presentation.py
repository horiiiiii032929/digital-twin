from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from xml.etree import ElementTree as E
import json,hashlib,re,shutil
R=Path.cwd();B=R/'reports/generated/cto-refined-build';O=R/'reports/presentation/deck'
ppt=O/'digital-twin-presentation-cto-refined.pptx';pdf=O/'digital-twin-presentation-cto-refined.pdf'
shutil.copyfile(B/'candidate-base.pdf',pdf)
s=json.loads((B/'deck-content.json').read_text())['slides']
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','c':'http://schemas.openxmlformats.org/drawingml/2006/chart','p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
with ZipFile(ppt) as z:
 slides=sorted((n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+.xml',n)),key=lambda x:int(re.search(r'slide(\d+)',x).group(1)))
 assert len(slides)==31
 text='\n'.join(' '.join(E.fromstring(z.read(n)).itertext()) for n in slides)
 assert not re.search(r'\b(appendix|backup)\b',text,re.I)
 for i,slide in enumerate(s,1):
  notes=E.fromstring(z.read(f'ppt/notesSlides/notesSlide{i}.xml'))
  t='\n'.join(v.text or '' for v in notes.findall('.//a:t',ns))
  assert all(p in t for p in slide['sources']),(i,'source mismatch')
 video=z.read('ppt/media/course-demo.mp4')
 assert hashlib.sha256(video).hexdigest()=='44f8cdc69d9fd64d5ca323bea6836519695373f47dabe77e81ed98399365f33b'
 assert b'rIdDemoMedia' in z.read('ppt/slides/slide4.xml')
 got=[]
 for n in sorted((n for n in z.namelist() if re.fullmatch(r'ppt/slides/charts/chart\d+.xml',n)),key=lambda x:int(re.search(r'chart(\d+)',x).group(1))):
  c=E.fromstring(z.read(n));got.extend([[float(v.text) for v in ser.findall('.//c:val//c:pt/c:v',ns)] for ser in c.findall('.//c:ser',ns)])
 expected=[ser['values'] for slide in s if slide['kind']=='charts' for c in slide['charts'] for ser in c['series']]
 assert got==expected,(got,expected)
report=R/'reports/submitted/2026-09-06/report-with-appendices.pdf'
assert hashlib.sha256(report.read_bytes()).hexdigest()=='240ec6154541d64394a102b4a4ebd2315eddd0f1584f021cfa559e5a84bfe909'

readme="""# Course Digital Twin — visual refinement

31 English main slides, six chapters, no appendix. The approved CTO / SDLC
narrative is retained. Diagrams, examples, comparisons and reading hierarchy
have been revised page by page.

- digital-twin-presentation-cto-refined.pptx: editable text, four tables and
  eight charts; unchanged 4:06 video embedded on slide 4, click to play.
- digital-twin-presentation-cto-refined.pdf: static review copy, no playable video.
- digital-twin-30-day-demo.mp4: separate full-window playback copy.
- diagrams/: ten draw.io originals plus their exported PNGs.
- cto-refined-slide-review.md: review and changes for each of the 31 pages.

Source references remain in PowerPoint notes. No new spoken script is included.
Video identity and native package relationships are checked; native PowerPoint
playback and a timed English rehearsal have not been exercised locally.
"""
(O/'README-cto-refined.md').write_text(readme)
used=sorted(set(slide['image'] for slide in s if slide.get('image','').startswith('reports/presentation/diagrams/cto-refined/')))
with ZipFile(O/'presentation-package-cto-refined.zip','w',ZIP_DEFLATED) as z:
 for p in [ppt,pdf,O/'README-cto-refined.md',O/'digital-twin-30-day-demo.mp4',R/'reports/presentation/cto-refined-slide-review.md']:z.write(p,p.name)
 for p in used:
  for f in [R/p,(R/p).with_suffix('.drawio')]:z.write(f,'diagrams/'+f.name)
(B/'delivery-checks.json').write_text(json.dumps(dict(slides=31,embedded_video_slide=4,chart_series_match=True,notes_sources_match=True,no_appendix=True,report_unchanged=True,diagram_count=len(used),pptx_sha256=hashlib.sha256(ppt.read_bytes()).hexdigest()),indent=2))
print('Verified chart data, 31 source-note mappings, video identity and unchanged submitted report; packaged output.')
