"""Sync the reviewed read-aloud narration into slide notes and a local reader."""
from pathlib import Path
import html
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'reports/generated/slide-build'
OUT = ROOT / 'reports/presentation/deck'
SOURCE = ROOT / 'reports/presentation/script/natural-narration.md'


def run():
    source = SOURCE.read_text()
    parts = re.split(r'^## (\d+)\. (.+)$', source, flags=re.M)
    data = json.loads((BUILD / 'deck-content.json').read_text())
    assert len(data['slides']) == 49
    before = [{k: v for k, v in s.items() if k != 'notes'} for s in data['slides']]
    bodies = {}
    sections = []
    main_words = 0
    for i in range(1, len(parts), 3):
        number = int(parts[i])
        title = parts[i + 1]
        body = parts[i + 2].split('# Optional backup responses')[0].strip()
        slide = data['slides'][number - 1]
        bodies[number] = body
        slide['notes'] = re.sub(r'^### (.+)$', r'[\1]', body, flags=re.M)
        spoken = re.sub(r'^###.*$', '', body, flags=re.M)
        if number <= 32:
            main_words += len(spoken.split())
        paragraphs = []
        for p in body.split('\n\n'):
            if p.startswith('### '):
                paragraphs.append('<aside>' + html.escape(p[4:]) + '</aside>')
            else:
                paragraphs.append('<p>' + html.escape(p) + '</p>')
        label = 'MAIN TALK' if number <= 32 else ('QUESTIONS' if number == 33 else 'OPTIONAL BACKUP')
        sections.append(f'<section id="slide-{number}"><small>{label} · SLIDE {number}</small>'
                        f'<h2>{html.escape(title)}</h2>{"".join(paragraphs)}</section>')
    assert set(bodies) == set(range(1, 50))
    assert before == [{k: v for k, v in s.items() if k != 'notes'} for s in data['slides']]
    data['main_word_count'] = main_words
    (BUILD / 'deck-content.json').write_text(json.dumps(data, indent=2))
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(SOURCE, OUT / 'speaker-script-natural.md')
    options = ''.join(f'<option value="slide-{s["number"]}">{s["number"]}. {html.escape(s["title"].strip())}</option>' for s in data['slides'])
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Digital Twin — read-aloud script</title>
<style>
:root{--reading-size:25px}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:110px}
body{margin:0;background:#faf9f6;color:#172b45;font-family:Arial,sans-serif}
nav{position:sticky;top:0;background:#fff;border-bottom:1px solid #d6dce2;padding:14px 24px;display:flex;gap:12px;align-items:center;z-index:1}
select{max-width:65vw;flex:1;padding:10px;font:16px Arial}button{padding:10px 14px;border:1px solid #b5bec7;background:white;border-radius:5px;font:16px Arial;cursor:pointer}
main{max-width:890px;margin:auto;padding:35px 32px 100px}.intro{font-size:18px;line-height:1.6;color:#526173}
section{padding:50px 0;border-bottom:1px solid #ced5dd;scroll-margin-top:15px}small{font-size:14px;letter-spacing:1px;color:#526173}h1{font-size:32px}h2{font-size:24px;line-height:1.35;margin:14px 0 30px}p{font-size:var(--reading-size);line-height:1.65;margin:0 0 25px}aside{background:#e8eef4;border-left:4px solid #496d91;padding:20px;margin:28px 0;font-size:18px;line-height:1.6}
@media print{nav{display:none}body{background:white}main{padding:0;max-width:none}section{break-before:page;padding-top:15px}p{font-size:14pt;line-height:1.5}h2{font-size:17pt}.intro{font-size:12pt}}
</style><nav aria-label="Reading controls"><select id="jump" aria-label="Go to slide">OPTIONS</select><button id="smaller" aria-label="Smaller text">A−</button><button id="larger" aria-label="Larger text">A+</button></nav>
<main><h1>Read-aloud script</h1><div class="intro">Read the paragraphs. Slide headings are for navigation. The shaded video cue is an action, not spoken narration. Backup responses start at slide 34.<br>WORDS words in the main talk, plus the 4:06 video. About 32.7–34.4 minutes at 180–170 words per minute, before pauses and transitions.</div>SECTIONS</main>
<script>
let size=25;document.getElementById('jump').addEventListener('change',e=>document.getElementById(e.target.value).scrollIntoView());
for(const [id,step] of [['smaller',-2],['larger',2]])document.getElementById(id).addEventListener('click',()=>{size=Math.max(19,Math.min(39,size+step));document.documentElement.style.setProperty('--reading-size',size+'px')});
</script></html>'''
    page = page.replace('OPTIONS', options).replace('WORDS', f'{main_words:,}').replace('SECTIONS', ''.join(sections))
    (OUT / 'speaker-script-natural.html').write_text(page)
    (BUILD / 'natural-script-check.json').write_text(json.dumps({
        'slides': 49, 'main_words': main_words, 'video_seconds': 246,
        'minutes_at_170_wpm_before_pauses': main_words / 170 + 4.1,
        'minutes_at_180_wpm_before_pauses': main_words / 180 + 4.1,
        'visible_slide_content_unchanged': True,
    }, indent=2))
    print(f'Synced 49 notes; {main_words} main words. Visible slide content unchanged.')


if __name__ == '__main__':
    run()
