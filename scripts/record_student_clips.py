"""Record four real synthetic student sessions using Playwright CLI page video.

Requires the recording workspace, published courses, and an open CLI session
named recording-film. No desktop, microphone or browser chrome is captured.
"""
import json
from pathlib import Path
import subprocess
from scripts.recording_safety import require_recording_runtime

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/playwright/recording-film"
CLI = Path.home() / ".codex/skills/playwright/scripts/playwright_cli.sh"


def call(*args):
    result = subprocess.run([str(CLI), "--session", "recording-film", *args], cwd=ROOT,
                            text=True, capture_output=True, check=True)
    if "### Error" in result.stdout:
        raise RuntimeError(result.stdout)
    return result.stdout


def main():
    require_recording_runtime()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    actors = (("a1", 5180, "Systems", "What is cache coherence?"),
              ("a2", 5181, "Systems", "What is virtual memory?"),
              ("b1", 5182, "Release governance", "What does a release policy define?"),
              ("b2", 5183, "Release governance", "What are approval and withdrawal controls in a release policy?"))
    for actor, port, course, question in actors:
        call("goto", f"http://127.0.0.1:{port}/student")
        snapshot = call("snapshot")
        if course not in snapshot or 'textbox "Ask about this course"' not in snapshot:
            raise RuntimeError(f"Unexpected initial UI for {actor}: {snapshot}")
        call("run-code", 'async page => { await page.getByRole("button",{name:"New chat",exact:true}).click(); }')
        snapshot = call("snapshot")
        (OUTPUT / f"{actor}-before.txt").write_text(snapshot)
        call("video-start", f"output/playwright/recording-film/student-{actor}.webm", "--size", "1600x900")
        try:
            code = '''async page => {
              await page.waitForTimeout(1800);
              await page.getByRole("textbox",{name:"Ask about this course"}).fill(QUESTION);
              await page.waitForTimeout(1500);
              await page.getByRole("button",{name:"Send question",exact:true}).click();
              await page.getByRole("button",{name:/Open citation 1:/}).waitFor({state:"visible"});
              await page.waitForTimeout(7000);
              console.log(await page.locator("body").ariaSnapshot());
            }'''.replace("QUESTION", json.dumps(question))
            (OUTPUT / f"{actor}-answer.txt").write_text(call("run-code", code))
            # Fresh snapshot above establishes the actual citation before opening it.
            snapshot = call("snapshot")
            if "Open citation 1:" not in snapshot:
                raise RuntimeError(f"Missing citation for {actor}")
            call("run-code", '''async page => {
              await page.getByRole("button",{name:/Open citation 1:/}).click();
              await page.waitForTimeout(5500);
            }''')
            call("screenshot", "--filename", f"output/playwright/recording-film/student-{actor}.png")
        finally:
            call("video-stop")
        print(f"Recorded Student {actor.upper()}: {course}, actual answer and source region.", flush=True)


if __name__ == "__main__":
    main()
