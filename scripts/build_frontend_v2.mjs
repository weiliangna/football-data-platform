import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(scriptDir, '..');
const v2Root = resolve(projectRoot, 'frontend-v2');
const sourceDist = resolve(v2Root, 'dist');
const targetDist = resolve(projectRoot, 'frontend', 'dist');

if (!existsSync(resolve(v2Root, 'package.json'))) throw new Error('frontend-v2/package.json not found');

const npm = process.platform === 'win32' ? 'npm.cmd' : 'npm';
execFileSync(npm, ['run', 'build'], {
  cwd: v2Root,
  stdio: 'inherit',
  shell: process.platform === 'win32',
});

if (!existsSync(resolve(sourceDist, 'index.html'))) throw new Error('frontend-v2 build did not produce dist/index.html');
mkdirSync(dirname(targetDist), { recursive: true });
rmSync(targetDist, { recursive: true, force: true });
cpSync(sourceDist, targetDist, { recursive: true });
console.log('frontend build now uses frontend-v2/dist');
