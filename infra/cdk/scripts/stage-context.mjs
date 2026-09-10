// Build an allowlisted context: no course data, recordings, .env files, or reports.
import { cpSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '../../..');
const target = resolve(here, '../.build-context');
rmSync(target, { recursive: true, force: true });
mkdirSync(target, { recursive: true });
const files = [];
function copy(relative) {
  mkdirSync(dirname(join(target, relative)), { recursive: true });
  cpSync(join(root, relative), join(target, relative));
  files.push(relative);
}
function tree(relative, accept) {
  for (const item of readdirSync(join(root, relative), { withFileTypes: true })) {
    if (item.isSymbolicLink()) throw new Error(`Symlink in deployment source: ${relative}/${item.name}`);
    if (['node_modules', '__pycache__', 'dist', '.git'].includes(item.name) || item.name.startsWith('.')) continue;
    const path = `${relative}/${item.name}`;
    if (item.isDirectory()) tree(path, accept);
    else if (accept(path)) copy(path);
  }
}
for (const file of ['package.json', 'package-lock.json', 'pyproject.toml', 'uv.lock', 'README.md',
  'deploy/Dockerfile', 'deploy/Caddyfile']) copy(file);
tree('src', p => p.endsWith('.py'));
tree('services', p => p.endsWith('.py'));
tree('apps/web', p => /\.(tsx?|js|mjs|cjs|json|html|css|svg|png|ico|woff2?)$/.test(p) && !/\.(test|spec)\./.test(p));
tree('research/05_evaluation/profiles', p => p.endsWith('.json'));
for (const name of ['backup_runtime', 'bootstrap_admin', 'manage_runtime_data', 'restore_runtime',
  'run_ingestion_worker', 'proactive_outreach_worker', 'autonomous_tutoring_worker']) copy(`scripts/${name}.py`);
for (const name of ['autonomous-tutoring-r1-confirmation-002', 'governed-full-autonomy-v2-1-confirmation-001',
  'governed-full-autonomy-v2-1-release-binding-correction-001', 'governed-full-autonomy-v2-1-final-release-binding-001']) {
  copy(`research/05_evaluation/records/${name}.json`);
}
const manifest = {
  revision: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
  dirty: Boolean(execFileSync('git', ['status', '--porcelain'], { cwd: root, encoding: 'utf8' }).trim()),
  files: Object.fromEntries(files.sort().map(p => [p, createHash('sha256').update(readFileSync(join(target, p))).digest('hex')])),
};
writeFileSync(join(target, 'release-manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
console.log(`Staged ${files.length} allowlisted files; revision ${manifest.revision}; dirty=${manifest.dirty}`);
