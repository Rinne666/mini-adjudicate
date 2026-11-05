'use strict';

const { spawnSync } = require('child_process');

// Executable paths and script arguments never pass through a shell.
function findPython(spawn = spawnSync, env = process.env) {
  const candidates = env.MINI_ADJUDICATION_PYTHON
    ? [{ command: env.MINI_ADJUDICATION_PYTHON, prefix: [] }]
    : [
        { command: 'python3', prefix: [] },
        { command: 'python', prefix: [] },
        { command: 'py', prefix: ['-3'] },
      ];
  for (const candidate of candidates) {
    const result = spawn(candidate.command, [
      ...candidate.prefix, '-c',
      'import json,sys; print(json.dumps(list(sys.version_info[:3])))',
    ], { encoding: 'utf8', timeout: 10000, windowsHide: true });
    if (result.error || result.status !== 0) continue;
    try {
      const version = JSON.parse(result.stdout.trim());
      if (Array.isArray(version) && version.length === 3
          && version.every(Number.isInteger) && version[0] === 3 && version[1] >= 10) {
        return { ...candidate, version: version.join('.') };
      }
    } catch { /* Try the next interpreter when a launcher prints invalid output. */ }
  }
  return null;
}

function requirePython() {
  const python = findPython();
  if (!python) {
    throw new Error('Python 3.10 or later is required. Install python3/python, or set MINI_ADJUDICATION_PYTHON to its executable path.');
  }
  return python;
}

module.exports = { findPython, requirePython };
