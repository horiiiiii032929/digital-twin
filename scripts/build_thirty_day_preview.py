"""Render a read-only, source-linked historical replay preview; no model calls."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'reports/generated/final-profile-operational-dialogue-development-001-full-live-001'
OUT = ROOT / 'reports/generated/thirty-day-preview'
HISTORY = 'answer-seeking-socratic-t1-v2-autonomous-6209'
INK, MUTED, ACCENT = '#182337', '#546278', '#4055cf'


def rows(history: str, name: str) -> list[dict]:
    return [json.loads(line) for line in (SOURCE / history / name).read_text().splitlines()]


def font(size: int, bold: bool = False):
    name = 'Arial Bold.ttf' if bold else 'Arial.ttf'
    return ImageFont.truetype('/System/Library/Fonts/Supplemental/' + name, size)


def paragraph(draw, text, x, y, width, size=30, color=INK, bold=False):
    face = font(size, bold)
    for block in text.split('\n'):
        line = ''
        for word in block.split():
            trial = (line + ' ' + word).strip()
            if draw.textlength(trial, font=face) > width and line:
                draw.text((x, y), line, font=face, fill=color)
                y += size * 1.3
                line = word
            else:
                line = trial
        draw.text((x, y), line, font=face, fill=color)
        y += size * 1.3
    return y


def render(scene, index):
    im = Image.new('RGB', (1920, 1080), '#eef1f7')
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1920, 160), fill=INK)
    d.text((64, 27), '30 VIRTUAL DAYS  /  HISTORICAL REPLAY', font=font(25, True), fill='#b8c6ff')
    d.text((64, 72), scene['title'], font=font(44, True), fill='white')
    d.text((1856, 65), f"DAY {scene['day']:02d}", font=font(45, True), fill='white', anchor='ra')
    # All four histories retain fixed positions. Counts refer to the stated end-of-day boundary.
    cast = [('A1', 'Socratic', HISTORY), ('A2', 'Socratic', 'low-receptivity-socratic-t1-v2-autonomous-6209'),
            ('B1', 'Explanatory', 'answer-seeking-explanatory-t1-v2-autonomous-6209'),
            ('B2', 'Explanatory', 'low-receptivity-explanatory-t1-v2-autonomous-6209')]
    for n, (alias, profile, history) in enumerate(cast):
        x = 64 + n * 451
        d.rounded_rectangle((x, 185, x + 435, 310), 16, fill='white', outline=ACCENT if n == 0 else '#d6deea', width=3)
        d.text((x + 20, 200), f'{alias}  |  {profile}', font=font(26, True), fill=INK)
        sent = sum(r['day'] <= scene['count_day'] for r in rows(history, 'proactive.jsonl'))
        replied = sum(r['day'] <= scene['count_day'] and r['reason'] == 'proactive-reply' for r in rows(history, 'turns.jsonl'))
        d.text((x + 20, 245), f'{sent} follow-ups  /  {replied} replies', font=font(25), fill=MUTED)
    d.text((64, 325), f"Counters through end of Day {scene['count_day']} · Four independent synthetic histories", font=font(20), fill=MUTED)
    d.rounded_rectangle((64, 365, 1200, 880), 20, fill='white')
    d.text((94, 392), scene['label'], font=font(26, True), fill=ACCENT)
    y = paragraph(d, scene['text'], 94, 444, 1076, 32)
    assert y < 856, (index, y)
    d.rounded_rectangle((1224, 365, 1856, 880), 20, fill='#e1e7f7')
    d.text((1254, 395), 'WHAT TO NOTICE', font=font(25, True), fill=ACCENT)
    y = paragraph(d, scene['notice'], 1254, 455, 566, 31)
    assert y < 854, (index, y)
    d.text((64, 910), scene['caption'], font=font(29, True), fill=INK)
    for day in range(1, 31):
        x = 64 + (day - 1) * 60
        d.rounded_rectangle((x, 970, x + 49, 984), 5, fill=ACCENT if day <= scene['day'] else '#d0d7e3')
    d.text((64, 1010), 'Recorded service outputs · Synthetic students and time · Editorial replay, not product UI', font=font(22), fill=MUTED)
    path = OUT / f'{index:02d}.png'
    im.save(path)
    return path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    turns = rows(HISTORY, 'turns.jsonl')
    messages = rows(HISTORY, 'proactive.jsonl')
    actions = rows(HISTORY, 'autonomous-actions.jsonl')
    before = next(t for t in turns if t['day'] == 4 and t['reason'] == 'question-reply')
    reply = next(t for t in turns if t['day'] == 5 and t['reason'] == 'proactive-reply')
    next_reply = next(t for t in turns if t['day'] == 6 and t['reason'] == 'proactive-reply')
    msg = next(m['message'] for m in messages if m['day'] == 5)
    repeated = next(m['message'] for m in messages if m['day'] == 6)
    action = next(a for a in actions if a['proactive_trigger_id'] == msg['trigger_id'])
    assert reply['turn']['student_message']['created_at'] == msg['created_at']
    assert next_reply['turn']['student_message']['created_at'] == repeated['created_at']
    assert msg['content'] == repeated['content']
    assert all(action['validation_results'].values())
    scenes = [
        dict(day=4, count_day=3, seconds=7, title='What happens without a new student question?', label='A1 · DAY 4 · STUDENT ATTEMPT',
             text=before['student'], notice='The student has already given a correct attempt.\nTomorrow, the system will still send a follow-up.', caption='Start with the prior interaction. Watch what the system does next.'),
        dict(day=5, count_day=4, seconds=5, title='One virtual day passes', label='A1 · SCHEDULED PROCESSING',
             text='Day 4  →  Day 5\n\nThe scheduler processes due work before today\'s student questions.', notice='No new student question triggered this follow-up.\nElapsed time is simulated.', caption='Time jumps forward; the recorded event order is preserved.'),
        dict(day=5, count_day=4, seconds=10, title='The system selects a check-in', label='A1 · RECORDED DECISION',
             text='Action: send an in-app check-in.\n\nRecorded reason, paraphrased:\nThe objective is incomplete, uncertainty is sufficient, and attempts remain.', notice='Recorded checks passed:\n• Outreach consent\n• Approved profile\n• Current evidence\n• Frequency limit\n• Not paused', caption='This explains the recorded decision; it does not prove a real learning need.'),
        dict(day=5, count_day=4, seconds=12, title='A follow-up arrives without a new question', label='A1 · ACTUAL DELIVERED MESSAGE',
             text=msg['content'], notice='The system initiated this message.\n\nBut the content repeats course evidence after yesterday\'s correct attempt.', caption='Autonomous delivery is visible. Personalization is still questionable.'),
        dict(day=5, count_day=4, seconds=10, title='The student replies; the tutor fails safely', label='A1 · ACTUAL REPLY AND TUTOR OUTPUT',
             text='STUDENT\n'+reply['student']+'\n\nTUTOR\n'+reply['turn']['tutor_message']['content'], notice='The log labels this as a proactive reply on the same day.\n\nThe tutor did not produce a usable teaching response here.', caption='The unsuccessful response stays in the demo.'),
        dict(day=6, count_day=5, seconds=9, title='The next day, the same support is sent again', label='A1 · DAY 6 · REPEATED MESSAGE',
             text=repeated['content'], notice='Exactly the same check-in text as Day 5.\n\nThe student replies with the correct course fact this time.', caption='A second reply is recorded; improved learning is not established.'),
        dict(day=6, count_day=6, seconds=10, title='Delivery works. Useful intervention remains unresolved.', label='DAYS 4–6 · OBSERVED OUTCOME',
             text='A1: two follow-ups, two synthetic replies.\n\nB2: three follow-ups, no proactive replies.\n\nA1 also shows a safe failure and repeated support.', notice='The replay demonstrates:\nScheduled action → delivery → response.\n\nIt also exposes what needs to improve.', caption='Full version: advance through consent changes, restart, and Day 30.'),
    ]
    manifest = {'history': HISTORY, 'action': action, 'message_ids': [msg['id'], repeated['id']], 'scenes': scenes,
                'sources': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted(SOURCE.glob('*autonomous*/*.jsonl'))}}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    clips = []
    for i, scene in enumerate(scenes):
        png = render(scene, i)
        clip = OUT / f'{i:02d}.mp4'
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-loop', '1', '-i', str(png),
                        '-t', str(scene['seconds']), '-r', '25', '-an', '-c:v', 'libx264', '-preset', 'ultrafast',
                        '-crf', '20', '-pix_fmt', 'yuv420p', str(clip)], check=True)
        clips.append(clip)
    listing = OUT / 'concat.txt'
    listing.write_text(''.join(f"file '{p}'\n" for p in clips))
    final = OUT / 'day-4-to-6-preview.mp4'
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0',
                    '-i', str(listing), '-c', 'copy', '-movflags', '+faststart', str(final)], check=True)
    print(final)


if __name__ == '__main__':
    main()
