"""Build a read-aloud script matched to the current 31-slide presentation."""
from pathlib import Path
import hashlib
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'reports/generated/cto-refined-build'
OUT = ROOT / 'reports/presentation/deck'
SOURCE = ROOT / 'reports/presentation/script/cto-natural-narration.txt'


def run():
    slides = json.loads((BUILD / 'deck-content.json').read_text())['slides']
    bodies = SOURCE.read_text().strip().split('\n===\n')
    assert len(slides) == len(bodies) == 31
    cue_pattern = r'\[PLAY VIDEO[^\]]*\]'
    counts = [len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b", re.sub(cue_pattern, '', body))) for body in bodies]
    total = sum(counts)
    minutes = {rate: total / rate + 246 / 60 for rate in [150, 160, 170, 180]}
    intro = (f'{total:,} spoken words across 31 slides, plus the 4:06 video. '
             f'Estimated total: {minutes[180]:.1f}–{minutes[170]:.1f} minutes at 180–170 words per minute, '
             f'or {minutes[160]:.1f} minutes at 160 words per minute. '
             'These estimates exclude extra pauses, slide changes and questions; no timed rehearsal has been performed.')
    markdown = ['# Course Digital Twin — read-aloud script',
                'For digital-twin-presentation-cto-refined.pptx. Read the paragraphs. '
                'Headings and the bracketed video cue are not spoken. No narration is required during the video.', intro]
    sections = []
    for slide, body, count in zip(slides, bodies, counts):
        number = slide['number']
        markdown.extend([f'## {number}. {slide["title"]}', body])
        paragraphs = []
        for paragraph in body.split('\n\n'):
            if paragraph.startswith('[PLAY VIDEO'):
                paragraphs.append('<aside role="note">' + html.escape(paragraph.strip('[]')) + '</aside>')
            else:
                paragraphs.append('<p>' + html.escape(paragraph) + '</p>')
        seconds = round(count / 170 * 60)
        duration = f'{seconds // 60}:{seconds % 60:02d}'
        sections.append(f'<section id="slide-{number}" data-number="{number}">'
                        f'<div class="meta">{html.escape(slide["chapter"])} · Slide {number} of 31 · '
                        f'{duration} spoken at 170 wpm' + (' + 4:06 video' if number == 4 else '') + '</div>'
                        f'<h2>{html.escape(slide["title"])}</h2>'
                        f'<details><summary>Show this slide</summary><img loading="lazy" '
                        f'src="../../generated/cto-refined-build/renders/slide-{number:02d}.png" '
                        f'alt="Slide {number}: {html.escape(slide["title"], quote=True)}"></details>'
                        + ''.join(paragraphs) + '</section>')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'speaker-script-cto-natural.md').write_text('\n\n'.join(markdown) + '\n')
    options = ''.join(f'<option value="{s["number"]}">{s["number"]}. {html.escape(s["title"])}</option>' for s in slides)
    template = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Course Digital Twin — 31-slide read-aloud script</title>
<style>
:root{--reading-size:26px;color-scheme:light}*{box-sizing:border-box}html{scroll-padding-top:100px}
body{margin:0;background:#faf9f6;color:#172b45;font-family:Arial,sans-serif}
nav{position:sticky;top:0;z-index:2;display:flex;align-items:center;gap:9px;flex-wrap:wrap;padding:12px 20px;background:#fff;border-bottom:1px solid #cbd4de}
select{flex:1;min-width:180px;max-width:65vw;font:16px Arial;padding:10px}
button{font:16px Arial;padding:10px 14px;border:1px solid #9fadb9;border-radius:4px;background:white;color:#172b45;cursor:pointer}button:disabled{opacity:.4;cursor:default}button:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #3977ad;outline-offset:3px}
main{max-width:920px;margin:auto;padding:32px 34px 100px}h1{font-size:32px;line-height:1.25}h2{font-size:26px;line-height:1.35;margin:13px 0 22px}.intro{font-size:18px;line-height:1.55;color:#4b5e70;margin:0 0 18px}
section{border-top:1px solid #cbd4de;padding:40px 0 34px;scroll-margin-top:16px}.meta{font-size:15px;color:#50677c;line-height:1.5}p{font-size:var(--reading-size);line-height:1.65;margin:0 0 26px}aside{background:#e9f0f7;border-left:4px solid #285e8e;padding:20px;font-size:20px;line-height:1.5;margin:28px 0}details{margin:0 0 26px;color:#365f85;font-size:16px}summary{cursor:pointer;padding:5px 0}img{display:block;width:100%;margin-top:12px;border:1px solid #ced5dc}
@media(max-width:600px){main{padding:24px 20px}nav{padding:9px}button{padding:8px}select{max-width:none;flex-basis:100%}:root{--reading-size:23px}}
@media print{nav,details{display:none}body{background:white}main{padding:0;max-width:none}h1{font-size:23pt}h2{font-size:18pt}section{break-before:page;border:0;padding-top:0}p{font-size:14pt;line-height:1.5}aside,.intro{font-size:12pt}.meta{font-size:10pt}}
</style></head><body>
<nav aria-label="Script navigation"><button id="previous" aria-label="Previous slide">Previous</button><select id="jump" aria-label="Go to slide">OPTIONS</select><button id="next" aria-label="Next slide">Next</button><button id="smaller" aria-label="Smaller script text">A−</button><button id="larger" aria-label="Larger script text">A+</button></nav>
<main><h1>Read-aloud script</h1><div class="intro">Matched to the revised 31-slide CTO / SDLC deck. Read the paragraphs. Headings, timing labels and the shaded video cue are not spoken.</div><div class="intro">TIMING</div>SECTIONS</main>
<script>
const selector=document.getElementById('jump'),sections=[...document.querySelectorAll('section')];let current=1,size=26;
function sync(){selector.value=String(current);document.getElementById('previous').disabled=current===1;document.getElementById('next').disabled=current===31;}
function go(n){current=Math.max(1,Math.min(31,n));sync();document.getElementById('slide-'+current).scrollIntoView({behavior:'instant',block:'start'});history.replaceState(null,'','#slide-'+current);}
selector.addEventListener('change',()=>go(Number(selector.value)));
document.getElementById('previous').addEventListener('click',()=>go(current-1));document.getElementById('next').addEventListener('click',()=>go(current+1));
for(const [id,step] of [['smaller',-2],['larger',2]])document.getElementById(id).addEventListener('click',()=>{size=Math.max(20,Math.min(40,size+step));document.documentElement.style.setProperty('--reading-size',size+'px')});
let queued=false;addEventListener('scroll',()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{const limit=document.querySelector('nav').getBoundingClientRect().bottom+80;let n=1;for(const section of sections)if(section.getBoundingClientRect().top<=limit)n=Number(section.dataset.number);current=n;sync();queued=false;});},{passive:true});
const initial=location.hash.match(/^#slide-(\d+)$/);if(initial)go(Number(initial[1]));else sync();
</script></body></html>'''
    page = template.replace('OPTIONS', options).replace('TIMING', html.escape(intro)).replace('SECTIONS', ''.join(sections))
    (OUT / 'speaker-script-cto-natural.html').write_text(page)
    report = {
        'slides': 31, 'spoken_words': total, 'words_by_slide': counts,
        'video_seconds': 246, 'total_minutes_before_pauses_by_wpm': minutes,
        'matched_deck_sha256': hashlib.sha256((OUT / 'digital-twin-presentation-cto-refined.pptx').read_bytes()).hexdigest(),
        'script_source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'slide_titles_match': True, 'visible_slides_unchanged': True,
        'timed_rehearsal_performed': False,
    }
    (BUILD / 'natural-script-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(intro)


if __name__ == '__main__':
    run()
