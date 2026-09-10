"""Helpers for browser-only footage of the live virtual-time recording sandbox."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import httpx
from scripts.recording_safety import require_recording_runtime

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/playwright/autonomous-film'
CLI = Path.home() / '.codex/skills/playwright/scripts/playwright_cli.sh'
SESSION = 'autonomous-film'
API_PORT = 8018
WEB_PORT_BASE = 5178


def check_runtime():
    with httpx.Client(base_url=f'http://127.0.0.1:{API_PORT}', trust_env=False, timeout=5) as client:
        return require_recording_runtime(client)


def call(*args):
    result = subprocess.run([str(CLI), '--session', SESSION, *args], cwd=ROOT,
                            text=True, capture_output=True, check=True)
    if '### Error' in result.stdout:
        raise RuntimeError(result.stdout)
    return result.stdout


def code(body):
    origins = [f'http://127.0.0.1:{WEB_PORT_BASE + index}' for index in range(6)]
    guard = 'if (!' + json.dumps(origins) + '.some(origin => page.url() === origin || page.url().startsWith(origin + "/"))) throw new Error("Unexpected recording page");'
    return call('run-code', 'async page => {' + guard + body + '}')


def start(name):
    check_runtime()
    code('')
    OUT.mkdir(parents=True, exist_ok=True)
    call('video-start', str(OUT / (name + '.webm')), '--size', '1600x900')


def stop(name):
    try:
        call('screenshot', '--filename', str(OUT / (name + '.png')))
        (OUT / (name + '.txt')).write_text(call('snapshot'))
    finally:
        call('video-stop')


def advance(days):
    with httpx.Client(base_url=f'http://127.0.0.1:{API_PORT}', trust_env=False, timeout=120) as c:
        require_recording_runtime(c)
        r = c.post('/__recording/advance', headers={'X-Recording-Control':'local-synthetic-only'}, json={'days':days})
        r.raise_for_status()
        data = r.json()
    (OUT / f'day-{data["day"]}.json').write_text(json.dumps(data, indent=2))
    return data


def onboarding():
    check_runtime()
    from src.digital_twin.onboarding.demo import SUPERVISOR_DEMO_ANSWERS
    start('01-onboarding-a')
    try:
        for answer in SUPERVISOR_DEMO_ANSWERS:
            code('await page.getByRole("textbox", {name:"Setup assistant reply"}).fill('+json.dumps(answer)+');'
                 'const response = page.waitForResponse(r => r.url().includes("/api/onboarding/sessions/") && r.url().endsWith("/messages") && r.request().method() === "POST");'
                 'await page.getByRole("button", {name:"Send answer",exact:true}).click();'
                 'if (!(await response).ok()) throw new Error("Onboarding request failed");')
    finally:
        stop('01-onboarding-a')
    (OUT / 'onboarding-session.txt').write_text(call('eval', '() => localStorage.getItem("course-digital-twin.professor-onboarding.v1.professor-synthetic")'))


def student_turn(text):
    check_runtime()
    code('await page.getByRole("textbox",{name:"Ask about this course"}).fill('+json.dumps(text)+'); await page.waitForTimeout(500); await page.getByRole("button",{name:"Send question",exact:true}).click(); await page.waitForTimeout(1600);')
    snapshot = call('snapshot')
    if 'pending' in snapshot.lower() and 'clarification' in snapshot.lower() or 'I found more than one supported interpretation' in snapshot:
        code('await page.getByRole("textbox",{name:"Ask about this course"}).fill("1"); await page.getByRole("button",{name:"Send question",exact:true}).click(); await page.waitForTimeout(1600);')
    return call('snapshot')


def record_initial_students():
    actors = [('a1',WEB_PORT_BASE+2,'What is cache coherence?'), ('a2',WEB_PORT_BASE+3,'What is virtual memory?'),
              ('b1',WEB_PORT_BASE+4,'What does a release policy define?'), ('b2',WEB_PORT_BASE+5,'What are approval and withdrawal controls in a release policy?')]
    for alias, port, question in actors:
        call('goto', f'http://127.0.0.1:{port}/student')
        snapshot = call('snapshot')
        assert 'Ask about this course' in snapshot
        start('06-chat-'+alias)
        if alias != 'a1':
            code('await page.getByRole("button",{name:/Open tutor check-ins/}).click();')
            code('await page.getByRole("button",{name:"Settings",exact:true}).click();')
            snapshot = call('snapshot')
            assert 'Allow private tutor check-ins' in snapshot
            code('await page.getByRole("checkbox",{name:"Allow private tutor check-ins"}).check(); await page.waitForTimeout(500); await page.getByRole("button",{name:"Close tutor check-ins"}).click();')
        snapshot = student_turn(question)
        if alias == 'a1':
            snapshot = student_turn('My attempt: cache coherence keeps replicated processor data consistent.')
        (OUT / ('initial-'+alias+'.txt')).write_text(snapshot)
        code('await page.waitForTimeout(2500);')
        stop('06-chat-'+alias)
        print('Recorded '+alias, flush=True)


def main():
    global API_PORT, WEB_PORT_BASE, SESSION, OUT
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", choices=("onboarding", "students"))
    parser.add_argument("--api-port", type=int, default=8018)
    parser.add_argument("--web-port-base", type=int, default=5178)
    parser.add_argument("--session", default="autonomous-film")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    API_PORT, WEB_PORT_BASE, SESSION, OUT = args.api_port, args.web_port_base, args.session, args.output
    check_runtime()
    if args.scene == "onboarding":
        onboarding()
    else:
        record_initial_students()


if __name__ == "__main__":
    main()
