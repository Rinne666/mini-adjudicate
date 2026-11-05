'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const ROOT = path.resolve(__dirname, '..');

function sandbox(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'mini adjudication test '));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const home = path.join(root, 'home with spaces');
  fs.mkdirSync(home);
  return { root, home };
}

// Override only Node's homedir lookup in the child. Never modify HOME or the
// actual user's agent directories, including when running the packed CLI.
function callCli(home, args, packageRoot = ROOT, env = {}) {
  const loader = [
    'require("os").homedir = () => process.env.MINI_ADJ_TEST_HOME;',
    'try { process.exitCode = require(process.argv[1]).main(process.argv.slice(2)); }',
    'catch (error) { console.error("FAIL: " + error.message); process.exitCode = 1; }',
  ].join('\n');
  const result = spawnSync(process.execPath, ['-e', loader, path.join(packageRoot, 'bin', 'cli.js'), ...args], {
    encoding: 'utf8', timeout: 120000, maxBuffer: 8 * 1024 * 1024,
    env: { ...process.env, MINI_ADJ_TEST_HOME: home, ...env },
  });
  return { ...result, output: `${result.stdout || ''}${result.stderr || ''}${result.error ? result.error.message : ''}` };
}

function npmCli() {
  const candidates = [
    process.env.npm_execpath,
    path.join(path.dirname(process.execPath), 'node_modules', 'npm', 'bin', 'npm-cli.js'),
    path.resolve(path.dirname(process.execPath), '..', 'lib', 'node_modules', 'npm', 'bin', 'npm-cli.js'),
  ].filter(Boolean);
  const found = candidates.find((file) => fs.existsSync(file));
  if (!found) throw new Error('Run this smoke test through npm run test:package so npm_execpath is available.');
  return found;
}

function callNpm(args, cwd = ROOT) {
  const result = spawnSync(process.execPath, [npmCli(), ...args], {
    cwd, encoding: 'utf8', timeout: 120000, maxBuffer: 8 * 1024 * 1024,
  });
  if (result.error || result.status !== 0) {
    throw new Error(`npm ${args.join(' ')} failed: ${result.error || ''}\n${result.stdout}\n${result.stderr}`);
  }
  return result;
}

module.exports = { ROOT, sandbox, callCli, callNpm };
