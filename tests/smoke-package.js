'use strict';

const assert = require('assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { ROOT, callCli, callNpm } = require('./helpers');
const { payloadFiles } = require('../bin/cli');

const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'mini adjudication package '));
try {
  const source = path.join(temp, 'package source');
  for (const relative of Object.keys(payloadFiles(ROOT))) {
    const file = path.join(source, relative);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.copyFileSync(path.join(ROOT, relative), file);
  }
  fs.copyFileSync(path.join(ROOT, '.npmignore'), path.join(source, '.npmignore'));
  const cache = path.join(source, 'runtime', '__pycache__');
  fs.mkdirSync(cache);
  fs.writeFileSync(path.join(cache, 'release-smoke.pyc'), 'must never be published');
  const packed = callNpm(['pack', '--json', '--pack-destination', temp], source);
  const [metadata] = JSON.parse(packed.stdout.slice(packed.stdout.indexOf('[')));
  assert.ok(metadata.files.every((file) => !/(__pycache__|\.py[co]$)/.test(file.path)), 'package contains Python cache files');
  const archive = path.join(temp, metadata.filename);
  assert.ok(fs.statSync(archive).size > 0, 'npm did not produce a real tarball');
  const consumer = path.join(temp, 'consumer with spaces');
  fs.mkdirSync(consumer);
  fs.writeFileSync(path.join(consumer, 'package.json'), '{"name":"smoke-consumer","private":true}\n');
  callNpm(['install', '--ignore-scripts', '--no-audit', '--no-fund', '--package-lock=false', archive], consumer);
  const installedPackage = path.join(consumer, 'node_modules', 'mini-adjudication');
  const home = path.join(temp, 'test home');
  fs.mkdirSync(home);
  const run = (args, root = installedPackage) => {
    const result = callCli(home, args, root);
    assert.equal(result.status, 0, result.output);
    return result;
  };
  run(['install', '--all', '--link']); // npm sources must fall back to a copy.
  const userSkill = path.join(home, '.agents', 'skills', 'mini-adjudication');
  assert.equal(fs.lstatSync(userSkill).isSymbolicLink(), false);
  run(['doctor', '--full']);
  run(['update', '--all']);
  run(['uninstall', '--user']);
  run(['doctor']);
  // Commands and runtime must remain usable even after the npm cache vanishes.
  fs.rmSync(installedPackage, { recursive: true, force: true });
  const survivingSkill = path.join(home, '.zcode', 'skills', 'mini-adjudication');
  run(['run', 'check_skill_loaded.py'], survivingSkill);
  run(['uninstall', '--all'], survivingSkill);
  assert.equal(fs.existsSync(path.join(home, '.zcode', 'commands', 'adjudicate.md')), false);
  console.log(`OK: packed ${metadata.files.length} files; tarball install, full doctor, update, shared uninstall and cache independence passed`);
} finally {
  fs.rmSync(temp, { recursive: true, force: true });
}
