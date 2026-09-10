"""Caption actual browser footage; no explanatory slides or replay graphics."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'output/playwright/autonomous-film'
OUT = ROOT / 'reports/generated/autonomous-film'


def duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(path)],text=True))


def run(args):
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',*args],check=True)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    scenes=json.loads((RAW/'edit-plan.json').read_text())
    clips=[]
    for i,s in enumerate(scenes):
        source=RAW/(s['file']+'.webm')
        total=duration(source)
        start=s.get('start',0)
        if start<0:
            start=max(0,total+start)
        length=min(s.get('length',total-start),total-start)
        seconds=s['seconds']
        canvas=Image.new('RGBA',(1920,1080),(0,0,0,0));d=ImageDraw.Draw(canvas)
        d.rectangle((0,0,1920,54),fill='#162134')
        d.rectangle((0,1008,1920,1080),fill='#162134')
        face=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',29)
        small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',23)
        assert d.textlength(s['caption'],font=face)<1810,s['caption']
        d.text((55,16),s['label'],font=small,fill='white')
        d.text((1865,16),'Virtual time · Synthetic accounts · Deterministic baseline',font=small,fill='#c4cee3',anchor='ra')
        d.text((960,1030),s['caption'],font=face,fill='white',anchor='ma')
        overlay=OUT/f'{i:02d}-subtitles.png';canvas.save(overlay)
        clip=OUT/f'{i:02d}.mp4'
        crop = s.get('crop')
        crop_filter = ''
        if crop is not None:
            if (not isinstance(crop, list) or len(crop) != 4
                    or any(type(value) is not int for value in crop)):
                raise ValueError('crop must contain integer x, y, width, height')
            x, y, width, height = crop
            probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error',
                '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                '-of', 'json', str(source)], text=True))['streams'][0]
            if (min(x, y) < 0 or min(width, height) <= 0
                    or x + width > probe['width'] or y + height > probe['height']
                    or width * 9 != height * 16):
                raise ValueError('crop must be an in-bounds 16:9 source region')
            crop_filter = f'crop={width}:{height}:{x}:{y},'
        if length <= 0 or seconds <= 0:
            raise ValueError('scene durations must be positive')
        filters=f'[0:v]trim=start={start}:duration={length},setpts=(PTS-STARTPTS)*{seconds/length},fps=30,{crop_filter}scale=1696:954,pad=1920:1080:112:54:color=0x162134[v];[v][1:v]overlay=0:0:format=auto[out]'
        run(['-i',str(source),'-loop','1','-i',str(overlay),'-filter_complex',filters,'-map','[out]',
             '-t',str(seconds),'-an','-r','30','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',str(clip)])
        s.update(source_start=start,source_length=length,source_duration=total)
        clips.append(clip)
        print('Edited',s['file'],flush=True)
    listing=OUT/'concat.txt';listing.write_text(''.join(f"file '{p}'\n" for p in clips))
    final=OUT/'digital-twin-30-day-demo.mp4'
    run(['-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(final)])
    (OUT/'edit-manifest.json').write_text(json.dumps({'duration_seconds':sum(s['seconds'] for s in scenes),'scenes':scenes},indent=2))
    print(final)


if __name__=='__main__':
    main()
