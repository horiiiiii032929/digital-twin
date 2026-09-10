"""Launch the ordinary product UI for six isolated synthetic actors."""
from __future__ import annotations

import json
import argparse
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time

from scripts.recording_app import ACTORS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/generated/recording-workspace"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-port", type=int, default=8018)
    parser.add_argument("--web-port-base", type=int, default=5178)
    args = parser.parse_args()
    ports = [args.api_port, *range(args.web_port_base, args.web_port_base + len(ACTORS))]
    if len(set(ports)) != len(ports) or any(port < 1024 or port > 65535 for port in ports):
        parser.error("Recording ports must be distinct and between 1024 and 65535.")
    actors = [(label, account, args.web_port_base + i, role) for i, (label, account, _, role) in enumerate(ACTORS)]
    output = OUT / f"api-{args.api_port}"
    # Never fall through to another port and accidentally reuse another runtime.
    for port in ports:
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                raise SystemExit(f"Port {port} is occupied. Stop this recording workspace before restarting.")
    node = shutil.which("node")
    if not node or not (ROOT / "node_modules/vite/bin/vite.js").is_file():
        raise SystemExit("Node and installed workspace dependencies are required (npm ci).")
    output.mkdir(parents=True, exist_ok=True)
    configuration = ROOT / f"apps/web/node_modules/.cache/recording/vite.recording-{args.api_port}.mjs"
    configuration.parent.mkdir(parents=True, exist_ok=True)
    configuration.write_text('''import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({
  root: ROOT_VALUE, envDir: false,
  cacheDir: 'node_modules/.vite-recording-' + process.env.RECORDING_ACTOR_ID,
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': SOURCE_VALUE } },
  define: {
    'import.meta.env.VITE_AUTH_MODE': JSON.stringify('demo'),
    'import.meta.env.VITE_API_BASE_URL': JSON.stringify(''),
    'import.meta.env.VITE_PROFESSOR_ACCOUNT_ID': JSON.stringify(process.env.RECORDING_ACTOR_ID),
    'import.meta.env.VITE_STUDENT_ACCOUNT_ID': JSON.stringify(process.env.RECORDING_ACTOR_ID)
  },
  server: { host: '127.0.0.1', strictPort: true,
    proxy: { '/api': { target: API_ORIGIN_VALUE, changeOrigin: true } }
  }
});
'''.replace("ROOT_VALUE", json.dumps(str(ROOT / "apps/web")))
        .replace("SOURCE_VALUE", json.dumps(str(ROOT / "apps/web/src")))
        .replace("API_ORIGIN_VALUE", json.dumps(f"http://127.0.0.1:{args.api_port}")))
    children = []
    logs = []
    def stop(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        commands = [("api", [sys.executable, "-m", "uvicorn", "scripts.recording_app:create_recording_app",
                              "--factory", "--host", "127.0.0.1", "--port", str(args.api_port)], {})]
        for label, account_id, port, role in actors:
            commands.append((account_id, [node, str(ROOT / "node_modules/vite/bin/vite.js"),
                "--config", str(configuration), "--port", str(port)], {"RECORDING_ACTOR_ID": account_id}))
        for name, command, extra in commands:
            log = (output / f"{name}.log").open("w")
            logs.append(log)
            children.append(subprocess.Popen(command, cwd=ROOT, env={**os.environ, **extra},
                                              stdout=log, stderr=subprocess.STDOUT, start_new_session=True))
        deadline = time.monotonic() + 60
        pending = set(ports)
        while pending and time.monotonic() < deadline:
            if any(child.poll() is not None for child in children):
                raise RuntimeError(f"A recording process exited during startup. Inspect {OUT}.")
            for port in list(pending):
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        pending.remove(port)
                except OSError:
                    pass
            if pending:
                time.sleep(0.2)
        if pending:
            raise RuntimeError(f"Recording startup timed out on ports {sorted(pending)}. Inspect {OUT}.")
        print("Recording rehearsal: deterministic demo mode; fresh temporary SQLite state.", flush=True)
        (output / "runtime.json").write_text(json.dumps({"api_url": f"http://127.0.0.1:{args.api_port}", "actors": actors}, indent=2) + "\n")
        for label, _, port, role in actors:
            route = "/professor/setup" if role == "professor" else "/student"
            print(f"{label}: http://127.0.0.1:{port}{route}", flush=True)
        print(f"Logs: {OUT}\nCtrl+C stops only these seven processes. Restart resets the sandbox.", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(0.5)
        raise RuntimeError(f"A recording process exited. Inspect logs in {OUT}.")
    except KeyboardInterrupt:
        pass
    finally:
        for child in children:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        for log in logs:
            log.close()


if __name__ == "__main__":
    main()
