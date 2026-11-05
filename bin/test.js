#!/usr/bin/env node
'use strict';

const { spawnSync } = require('child_process');
const path = require('path');
const root = path.resolve(__dirname, '..');
for (const args of [
  [path.join(__dirname, 'cli.js'), 'run', 'regression.py'],
  ['--test', path.join(root, 'tests', 'cli.test.js')],
]) {
  const result = spawnSync(process.execPath, args, { cwd: root, stdio: 'inherit' });
  if (result.error) console.error(result.error.message);
  if (result.error || result.status !== 0) {
    process.exitCode = result.status || 1;
    break;
  }
}
