'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { findPython } = require('../bin/python');
const { payloadFiles } = require('../bin/cli');
const { ROOT, sandbox, callCli } = require('./helpers');

const skill = (home, scope = 'user') => path.join(home, { user: '.agents', zcode: '.zcode', claude: '.claude' }[scope], 'skills', 'mini-adjudication');
const command = (home) => path.join(home, '.zcode', 'commands', 'adjudicate.md');
const receipt = (home, scope = 'user') => path.join(path.dirname(skill(home, scope)), '.mini-adjudication.installation.json');
function ok(result) { assert.equal(result.status, 0, result.output); }

test('Python discovery rejects old interpreters and supports the Windows launcher', () => {
  const seen = [];
  const python = findPython((bin, args) => {
    seen.push([bin, args]);
    return { status: 0, stdout: JSON.stringify(bin === 'python3' ? [3, 9, 9] : bin === 'python' ? [2, 7, 18] : [3, 10, 16]) };
  }, {});
  assert.equal(python.command, 'py');
  assert.deepEqual(python.prefix, ['-3']);
  assert.equal(seen[2][1][0], '-3');
  const explicit = findPython((bin) => {
    assert.equal(bin, '/python with spaces/python');
    return { status: 0, stdout: '[3, 14, 0]' };
  }, { MINI_ADJUDICATION_PYTHON: '/python with spaces/python' });
  assert.equal(explicit.version, '3.14.0');
  assert.equal(findPython(() => ({ status: 0, stdout: '[3, 9, 0]' }), {}), null);
});

test('all scopes install; removing zcode preserves the user shared command', (t) => {
  const { home } = sandbox(t);
  ok(callCli(home, ['install', '--all']));
  ok(callCli(home, ['doctor']));
  ok(callCli(home, ['uninstall', '--zcode']));
  assert.ok(fs.existsSync(path.join(skill(home), 'SKILL.md')));
  assert.ok(fs.readFileSync(command(home), 'utf8').includes(skill(home).split(path.sep).join('/')));
  ok(callCli(home, ['doctor']));
  ok(callCli(home, ['uninstall', '--all']));
  assert.equal(fs.existsSync(command(home)), false);
});

test('removing user redirects the shared command to zcode', (t) => {
  const { home } = sandbox(t);
  ok(callCli(home, ['install', '--user', '--zcode']));
  ok(callCli(home, ['uninstall', '--user']));
  assert.ok(fs.readFileSync(command(home), 'utf8').includes(skill(home, 'zcode').split(path.sep).join('/')));
  ok(callCli(home, ['doctor']));
});

test('doctor rejects missing or edited commands and missing command targets', (t) => {
  const { home } = sandbox(t);
  ok(callCli(home, ['install']));
  const original = fs.readFileSync(command(home), 'utf8');
  fs.unlinkSync(command(home));
  assert.match(callCli(home, ['doctor']).output, /FAIL Missing trigger command/);
  fs.writeFileSync(command(home), `${original}\nlocal change\n`);
  assert.equal(callCli(home, ['doctor']).status, 1);
  fs.writeFileSync(command(home), original);
  fs.unlinkSync(path.join(skill(home), 'bin', 'cli.js'));
  assert.equal(callCli(home, ['doctor']).status, 1);
});

test('updates preserve extra files and reject overwriting a modified owned file', (t) => {
  const { home } = sandbox(t);
  ok(callCli(home, ['install']));
  const notes = path.join(skill(home), 'my-notes.md');
  fs.writeFileSync(notes, 'personal notes');
  ok(callCli(home, ['update']));
  assert.equal(fs.readFileSync(notes, 'utf8'), 'personal notes');
  const owned = path.join(skill(home), 'README.md');
  fs.appendFileSync(owned, '\nmy customization\n');
  const updated = callCli(home, ['update']);
  assert.equal(updated.status, 1);
  assert.match(updated.output, /Local file changes/);
  ok(callCli(home, ['uninstall']));
  assert.match(fs.readFileSync(owned, 'utf8'), /my customization/);
  assert.equal(fs.readFileSync(notes, 'utf8'), 'personal notes');
  assert.equal(fs.existsSync(command(home)), false);
});

test('an invalid package fails before replacing an existing installation', (t) => {
  const { root, home } = sandbox(t);
  ok(callCli(home, ['install']));
  const before = fs.readFileSync(path.join(skill(home), 'SKILL.md'), 'utf8');
  const broken = path.join(root, 'broken package');
  for (const relative of Object.keys(payloadFiles(ROOT))) {
    const dest = path.join(broken, relative);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(path.join(ROOT, relative), dest);
  }
  fs.appendFileSync(path.join(broken, 'SKILL.md'), '\nstale manifest\n');
  assert.equal(callCli(home, ['update'], broken).status, 1);
  assert.equal(fs.readFileSync(path.join(skill(home), 'SKILL.md'), 'utf8'), before);
  ok(callCli(home, ['doctor']));
});

test('unmanaged directories and commands are preserved', (t) => {
  const { home } = sandbox(t);
  fs.mkdirSync(path.dirname(command(home)), { recursive: true });
  fs.writeFileSync(command(home), 'my other command');
  assert.equal(callCli(home, ['install']).status, 1);
  assert.equal(fs.readFileSync(command(home), 'utf8'), 'my other command');
  assert.equal(fs.existsSync(skill(home)), false);
  fs.unlinkSync(command(home));
  fs.mkdirSync(skill(home), { recursive: true });
  fs.writeFileSync(path.join(skill(home), 'personal.txt'), 'keep');
  assert.equal(callCli(home, ['install']).status, 1);
  assert.equal(fs.readFileSync(path.join(skill(home), 'personal.txt'), 'utf8'), 'keep');
});

test('legacy installations migrate with retained backups', (t) => {
  const { home } = sandbox(t);
  ok(callCli(home, ['install']));
  fs.unlinkSync(receipt(home));
  fs.unlinkSync(`${command(home)}.mini-adjudication.json`);
  const result = callCli(home, ['update']);
  ok(result);
  const data = JSON.parse(fs.readFileSync(receipt(home), 'utf8'));
  assert.ok(fs.existsSync(path.join(data.retained_backup, 'SKILL.md')));
  assert.match(result.output, /retained legacy command backup/);
  ok(callCli(home, ['doctor']));
});

test('link install and removal leave the checkout intact; installed CLI cannot self-link', (t) => {
  const { home } = sandbox(t);
  ok(callCli(home, ['install', '--link']));
  const data = JSON.parse(fs.readFileSync(receipt(home), 'utf8'));
  assert.equal(data.mode, 'link');
  ok(callCli(home, ['uninstall']));
  assert.ok(fs.existsSync(path.join(ROOT, 'SKILL.md')));
  ok(callCli(home, ['install']));
  ok(callCli(home, ['update', '--link'], skill(home)));
  assert.equal(fs.lstatSync(skill(home)).isSymbolicLink(), false);
  ok(callCli(home, ['doctor']));
});

test('managed paths never follow a replacement directory symlink during uninstall', (t) => {
  const { root, home } = sandbox(t);
  ok(callCli(home, ['install']));
  const outside = path.join(root, 'outside');
  const runtime = path.join(skill(home), 'runtime');
  fs.renameSync(runtime, outside);
  fs.symlinkSync(outside, runtime, process.platform === 'win32' ? 'junction' : 'dir');
  const result = callCli(home, ['uninstall']);
  assert.equal(result.status, 1);
  assert.match(result.output, /crosses a local symlink/);
  assert.ok(fs.existsSync(path.join(outside, 'validate_adjudication.py')));
});

test('generated quoted launcher works from an installed path containing spaces', (t) => {
  const { home } = sandbox(t);
  ok(callCli(home, ['install']));
  const text = fs.readFileSync(command(home), 'utf8');
  const line = text.split('\n').find((value) => value.includes(' run check_skill_loaded.py'));
  assert.ok(line.startsWith("node '"));
  assert.equal(line.includes('\\runtime\\'), false);
  const result = process.platform === 'win32'
    ? spawnSync('powershell.exe', ['-NoProfile', '-Command', line], { encoding: 'utf8' })
    : spawnSync('/bin/sh', ['-c', line], { encoding: 'utf8' });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  ok(callCli(home, ['run', 'cvss31.py', '--selftest'], skill(home)));
  assert.equal(callCli(home, ['run', '../SKILL.md']).status, 1);
});

test('cnvd-packager skill and /cnvd-pack command install, link, verify, and uninstall distinctly from /adjudicate', (t) => {
  const { home } = sandbox(t);
  const cnvdSkill = (scope = 'user') => path.join(home, { user: '.agents', zcode: '.zcode', claude: '.claude' }[scope], 'skills', 'cnvd-packager');
  const cnvdCmd = (scope = 'user') => path.join(home, scope === 'claude' ? '.claude' : '.zcode', 'commands', 'cnvd-pack.md');
  ok(callCli(home, ['install', '--all']));
  assert.ok(fs.existsSync(path.join(cnvdSkill('user'), 'SKILL.md')));
  assert.ok(fs.existsSync(path.join(cnvdSkill('user'), 'references', 'report-template.md')));
  assert.ok(fs.existsSync(path.join(cnvdSkill('user'), 'references', 'video-production.md')));
  assert.ok(fs.existsSync(path.join(cnvdSkill('user'), 'scripts', 'verify_cnvd_package.py')));
  assert.ok(fs.existsSync(path.join(cnvdSkill('zcode'), 'SKILL.md')));
  assert.ok(fs.existsSync(path.join(cnvdSkill('claude'), 'SKILL.md')));
  const cmdText = fs.readFileSync(cnvdCmd('user'), 'utf8');
  assert.match(cmdText, /# \/cnvd-pack/);
  assert.ok(cmdText.includes(cnvdSkill('user').split(path.sep).join('/')));
  assert.ok(cmdText.includes(skill(home, 'user').split(path.sep).join('/')));
  const line = cmdText.split('\n').find((value) => value.includes(' run check_skill_loaded.py'));
  const res = process.platform === 'win32'
    ? spawnSync('powershell.exe', ['-NoProfile', '-Command', line], { encoding: 'utf8' })
    : spawnSync('/bin/sh', ['-c', line], { encoding: 'utf8' });
  assert.equal(res.status, 0, `${res.stdout}\n${res.stderr}`);
  ok(callCli(home, ['uninstall', '--user']));
  assert.equal(fs.existsSync(cnvdSkill('user')), false);
  assert.ok(fs.readFileSync(cnvdCmd('user'), 'utf8').includes(cnvdSkill('zcode').split(path.sep).join('/')));
  ok(callCli(home, ['doctor']));
  ok(callCli(home, ['uninstall', '--all']));
  assert.equal(fs.existsSync(cnvdCmd('user')), false);
  assert.equal(fs.existsSync(cnvdCmd('claude')), false);
});
