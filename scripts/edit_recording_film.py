"""Edit browser-only captures into a captioned 1080p presentation film.

The last chapter visualizes a separately executed domain-service trace. It is
explicitly labelled and is not passed off as product screen recording.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "output/playwright/recording-film"
OUT = ROOT / "reports/generated/recording-film"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
INK = "#19191d"
MUTED = "#62636e"
ACCENT = "#5450d6"


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(path)], text=True))


def ffmpeg(arguments):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *arguments], check=True)


def encode_args(path, seconds):
    return ["-t", str(seconds), "-an", "-r", "30", "-c:v", "libx264", "-preset", "fast", "-crf", "19",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)]


def chrome(title, caption, label="Recorded product UI  /  Synthetic demo"):
    image = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1920, 54), fill="white")
    draw.rectangle((0, 1026, 1920, 1080), fill="white")
    draw.text((96, 13), title, font=font(26, True), fill=INK)
    draw.text((1824, 17), label, font=font(19), fill=MUTED, anchor="ra")
    draw.text((960, 1041), caption, font=font(25), fill=INK, anchor="ma")
    return image


def card(title, subtitle, rows, *, footnote, filename):
    image = Image.new("RGB", (1920, 1080), "white")
    draw = ImageDraw.Draw(image)
    draw.line((96, 96, 1824, 96), fill=ACCENT, width=5)
    draw.text((96, 146), "COURSE DIGITAL TWIN", font=font(23, True), fill=ACCENT)
    draw.text((96, 227), title, font=font(65, True), fill=INK)
    draw.text((96, 325), subtitle, font=font(29), fill=MUTED)
    for index, (left, middle, right) in enumerate(rows):
        y = 485 + index * 142
        draw.line((96, y - 30, 1824, y - 30), fill="#e1e2e7", width=2)
        draw.text((106, y), left, font=font(32, True), fill=INK)
        draw.text((590, y), middle, font=font(30), fill=INK)
        draw.text((1230, y), right, font=font(29), fill=ACCENT)
    draw.text((96, 961), footnote, font=font(24), fill=MUTED)
    image.save(OUT / filename)
    return OUT / filename


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    segments = []
    manifest = []
    def still(path, seconds, name):
        dest = OUT / f"{len(segments):02d}-{name}.mp4"
        ffmpeg(["-loop", "1", "-i", str(path), *encode_args(dest, seconds)])
        segments.append(dest)
        manifest.append({"chapter": name, "seconds": seconds, "source": str(path.relative_to(ROOT)), "type": "editorial card"})
    def clip(file, seconds, title, caption, *, start=0, length=None, name=None):
        source = RAW / file
        length = length or duration(source) - start
        stem = name or source.stem
        overlay = OUT / f"{len(segments):02d}-caption.png"
        chrome(title, caption).save(overlay)
        dest = OUT / f"{len(segments):02d}-{stem}.mp4"
        filters = (f"[0:v]trim=start={start}:duration={length},setpts=(PTS-STARTPTS)*{seconds/length},"
                   "fps=30,scale=1728:972,pad=1920:1080:96:54:color=0xf4f5f8[screen];"
                   "[screen][1:v]overlay=0:0:format=auto[v]")
        ffmpeg(["-i", str(source), "-loop", "1", "-i", str(overlay), "-filter_complex", filters,
                "-map", "[v]", *encode_args(dest, seconds)])
        segments.append(dest)
        manifest.append({"chapter": stem, "seconds": seconds, "source": str(source.relative_to(ROOT)),
                         "source_start": start, "source_length": length, "type": "browser-only screen recording"})

    still(card("From setup to student support", "An edited software walkthrough with two instructors and four students.",
        [("Professor A", "Systems", "Student A1 + Student A2"),
         ("Professor B", "Release governance", "Student B1 + Student B2")],
        footnote="Synthetic accounts and materials. Deterministic baseline. No real classroom data.", filename="intro.png"), 7, "intro")
    clip("01-onboarding.webm", 24, "01  Instructor onboarding", "The instructor defines sources, teaching preferences and academic-integrity limits.")
    source_duration = duration(RAW / "02-sources.webm")
    clip("02-sources.webm", 14, "02  Source permission", "Register the file metadata and approve its permitted use. Repetitive steps are shortened.",
         start=14, length=source_duration-14)
    clip("03-review.webm", 12, "03  Review before release", "Inspect the synthetic policy preview and the completed release checklist.")
    clip("04-upload-publish.webm", 20, "04  PDF ingestion and publication", "Import approved evidence, run the release checks, then publish to students.")
    clip("07-instructor-control.webm", 5, "05  A separate instructor and course", "Professor B owns Release governance and its two assigned students.", length=5, name="second-course")
    clip("05-consent.webm", 11, "06  Student consent", "Private check-ins are optional. The student can turn them off at any time.", start=1, length=11)
    clip("student-a1.webm", 14, "07  A course-grounded conversation", "Student A1 asks about cache coherence. The answer uses the approved course material.", length=14, name="student-question")
    clip("student-a1.webm", 8, "08  Inspect the source", "The citation opens the actual source region, version and course-release lineage.",
         start=duration(RAW / "student-a1.webm")-7, length=7, name="source-citation")

    # Show four real recorded conversations together. These actions were executed
    # sequentially; the layout is explicitly labelled as an edited comparison.
    overlay = chrome("09  Four students, two course contexts", "Four recorded sessions shown together; this is not a concurrent-load test.",
                     "Edited comparison  /  Synthetic recordings")
    draw = ImageDraw.Draw(overlay)
    inputs = []
    filters = []
    for index, actor in enumerate(("a1", "a2", "b1", "b2")):
        source = RAW / f"student-{actor}.webm"
        inputs += ["-sseof", "-6", "-i", str(source)]
        filters.append(f"[{index}:v]crop=900:330:285:85,scale=900:330,setsar=1,fps=30,tpad=stop_mode=clone:stop_duration=16,tile=1x1[p{index}]")
        x = 44 if index < 2 else 976
        y = 86 if index % 2 == 0 else 553
        course = "Systems" if index < 2 else "Release governance"
        draw.rectangle((x, y, x+900, y+415), fill="white")
        draw.text((x+22, y+17), f"Student {actor.upper()}  /  {course}", font=font(27, True), fill=INK)
    grid_base = Image.new("RGB", (1920, 1080), "#f4f5f8")
    grid_base.paste(overlay, mask=overlay.getchannel("A"))
    grid_base.save(OUT / "grid-base.png")
    inputs += ["-loop", "1", "-i", str(OUT / "grid-base.png")]
    chain = "[4:v][p0]overlay=44:151[g0];[g0][p1]overlay=44:618[g1];[g1][p2]overlay=976:151[g2];[g2][p3]overlay=976:618[v]"
    dest = OUT / f"{len(segments):02d}-four-students.mp4"
    ffmpeg([*inputs, "-filter_complex", ";".join(filters)+";"+chain, "-map", "[v]", *encode_args(dest,16)])
    segments.append(dest)
    manifest.append({"chapter":"four-students", "seconds":16, "type":"edited comparison of four browser recordings"})
    clip("07-instructor-control.webm", 12, "10  Instructor control", "Professor B pauses autonomous processing. Pausing preserves goals and pending work.",
         start=duration(RAW / "07-instructor-control.webm")-17, length=17, name="instructor-pause")

    trace_path = ROOT / "apps/web/public/recording-demo.json"
    trace = json.loads(trace_path.read_text())
    supports = [e for e in trace["events"] if e["kind"] == "support"]
    assert len(supports[0]["data"]["inbox"]) == 1
    assert supports[1]["data"]["inbox"] == []
    assert supports[1]["data"]["opportunity"]["status"] == "pending"
    assert sum(trace["events"][-1]["data"]["inbox_counts"].values()) == 1
    shutil.copyfile(trace_path, OUT / "service-replay.json")
    foot = "Separate deterministic service execution; scripted opportunities. Not a learning-effect evaluation."
    still(card("Later support: service-event replay", "The following log visualization uses a separate synthetic service run.",
        [("Day 1", "Student A1", "Practice scheduled"), ("Day 1", "Student B2", "Practice scheduled")],
        footnote=foot, filename="replay-schedule.png"),6,"replay-schedule")
    still(card("Day 2: the virtual clock advances", "A one-day clock advance makes the scripted opportunities due.",
        [("Professor A", "Systems", "Support enabled"), ("Professor B", "Release governance", "Processing paused")],
        footnote=foot, filename="replay-clock.png"),6,"replay-clock")
    still(card("Delivery follows the instructor boundary", "Actual saved outcomes from the separate service replay.",
        [("Student A1", "1 private practice message", "Delivered"),
         ("Student B2", "0 private practice messages", "Pending while paused"),
         ("Worker retry", "1 total message remains", "No additional delivery")],
        footnote=foot, filename="replay-results.png"),9,"replay-results")
    still(card("Inspectable software behaviour", "Instructor setup, approved evidence, separate conversations and continuing control.",
        [("Source boundary", "Approved course material", "Citations remain visible"),
         ("Human control", "Consent and pause", "Explicit permissions")],
        footnote="Synthetic demonstration only. This video does not establish learning improvement or model quality.",
        filename="outro.png"),6,"outro")
    concat = OUT / "concat.txt"
    concat.write_text("".join(f"file '{p.name}'\n" for p in segments))
    final = OUT / "course-digital-twin-demo.mp4"
    ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(final)])
    (OUT / "edit-manifest.json").write_text(json.dumps({"duration_seconds":sum(x["seconds"] for x in manifest),
         "format":"1920x1080, 30 fps, H.264, silent", "chapters":manifest}, indent=2)+"\n")
    print(final, flush=True)


if __name__ == "__main__":
    main()
