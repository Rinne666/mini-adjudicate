#!/usr/bin/env node
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');
const { findPython, requirePython } = require('./python');

const PKG_ROOT = path.resolve(__dirname, '..');
const SKILL_NAME = 'mini-adjudication';
const PAYLOAD = new Set([
  'bin', 'cli', 'package.json', 'SKILL.md', 'README.md', 'references',
  'templates', 'schemas', 'runtime', 'fixtures', '_meta.json',
]);
const SCOPES = ['user', 'zcode', 'claude'];
const MARKER = '<!-- mini-adjudication managed command v1 -->';
const HOOK_NOTICE = 'Hooks are not registered or verified by this installer. Run the phase gates manually unless you have separately configured and tested your harness hooks.';

function skillRoot(scope) {
  return path.join(os.homedir(), { user: '.agents', zcode: '.zcode', claude: '.claude' }[scope], 'skills');
}
function skillDir(scope) { return path.join(skillRoot(scope), SKILL_NAME); }
function receiptPath(scope) { return path.join(skillRoot(scope), `.${SKILL_NAME}.installation.json`); }
function commandPath(scope) {
  return path.join(os.homedir(), scope === 'claude' ? '.claude' : '.zcode', 'commands', 'adjudicate.md');
}
function commandReceiptPath(scope) { return `${commandPath(scope)}.mini-adjudication.json`; }
function exists(file) {
  try { fs.lstatSync(file); return true; } catch (error) {
    if (error.code === 'ENOENT') return false;
    throw error;
  }
}
function sha(data) { return crypto.createHash('sha256').update(data).digest('hex'); }
function readJson(file) { return JSON.parse(fs.readFileSync(file, 'utf8')); }
function readReceipt(scope) {
  const file = receiptPath(scope);
  if (!exists(file)) return null;
  const receipt = readJson(file);
  if (receipt.schema_version !== 1 || receipt.scope !== scope
      || !['copy', 'link'].includes(receipt.mode) || receipt.destination !== skillDir(scope)
      || !receipt.files || typeof receipt.files !== 'object' || Array.isArray(receipt.files)) {
    throw new Error(`Invalid installation receipt: ${file}`);
  }
  for (const [name, hash] of Object.entries(receipt.files)) {
    safeChild(skillDir(scope), name);
    if (!/^[a-f0-9]{64}$/.test(hash)) throw new Error(`Invalid file hash in ${file}`);
  }
  return receipt;
}
function safeChild(root, relative) {
  if (typeof relative !== 'string' || !relative || relative.includes('\\') || path.isAbsolute(relative)) {
    throw new Error(`Invalid managed path: ${relative}`);
  }
  const child = path.resolve(root, relative);
  const rel = path.relative(root, child);
  if (!rel || rel.startsWith(`..${path.sep}`) || rel === '..' || path.isAbsolute(rel)) {
    throw new Error(`Managed path escapes its directory: ${relative}`);
  }
  for (let parent = path.dirname(child); parent !== path.resolve(root); parent = path.dirname(parent)) {
    if (exists(parent) && fs.lstatSync(parent).isSymbolicLink()) {
      throw new Error(`Managed path crosses a local symlink; preserving it: ${parent}`);
    }
  }
  return child;
}
function atomicWrite(file, text) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temp = `${file}.tmp-${crypto.randomUUID()}`;
  try { fs.writeFileSync(temp, text); fs.renameSync(temp, file); }
  finally { if (exists(temp)) fs.unlinkSync(temp); }
}
function removePath(file) {
  if (!exists(file)) return;
  if (fs.lstatSync(file).isSymbolicLink()) fs.unlinkSync(file);
  else fs.rmSync(file, { recursive: true, force: true });
}
function isPayload(relative) {
  const parts = relative.split(path.sep);
  return PAYLOAD.has(parts[0]) && !parts.includes('__pycache__')
    && !parts.some((part) => /\.(py[co]|tgz)$/.test(part));
}
function payloadFiles(root) {
  const result = {};
  function visit(dir) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const file = path.join(dir, entry.name);
      const relative = path.relative(root, file);
      if (!isPayload(relative)) continue;
      if (entry.isSymbolicLink()) throw new Error(`Package payload must not contain a symlink: ${relative}`);
      if (entry.isDirectory()) visit(file);
      else if (entry.isFile()) result[relative.split(path.sep).join('/')] = sha(fs.readFileSync(file));
    }
  }
  visit(root);
  return result;
}
function verifyManifest(root) {
  const manifest = readJson(path.join(root, 'runtime', 'skill_manifest.json'));
  if (!manifest.files || !Object.keys(manifest.files).length) throw new Error('Skill manifest has no files');
  for (const [relative, hash] of Object.entries(manifest.files)) {
    const file = safeChild(root, relative);
    if (!exists(file) || sha(fs.readFileSync(file)) !== hash) {
      throw new Error(`Skill manifest mismatch: ${relative}. Repair the package before installing.`);
    }
  }
}
function shellQuote(value) {
  const portable = value.split(path.sep).join('/');
  return process.platform === 'win32'
    ? `'${portable.replaceAll("'", "''")}'`
    : `'${portable.replaceAll("'", "'\\''")}'`;
}
function renderCommand(dest, root = PKG_ROOT) {
  return fs.readFileSync(path.join(root, 'cli', 'commands', 'adjudicate.md'), 'utf8')
    .replaceAll('{{SKILL_DIR}}', dest.split(path.sep).join('/'))
    .replaceAll('{{CLI_COMMAND}}', `node ${shellQuote(path.join(dest, 'bin', 'cli.js'))}`)
    .replaceAll('{{SHELL_NAME}}', process.platform === 'win32' ? 'Windows PowerShell' : 'POSIX shell');
}
function groupScopes(scope) { return scope === 'claude' ? ['claude'] : ['user', 'zcode']; }
function assertCommandOwned(scope) {
  const file = commandPath(scope);
  if (!exists(file)) return;
  const text = fs.readFileSync(file, 'utf8');
  const receiptFile = commandReceiptPath(scope);
  if (exists(receiptFile)) {
    const receipt = readJson(receiptFile);
    if (receipt.schema_version === 1 && receipt.sha256 === sha(text) && text.includes(MARKER)) return;
    throw new Error(`The command was changed outside the installer; preserving it: ${file}`);
  }
  // Migrate recognizable legacy commands with a backup. Merely mentioning
  // the skill name is not enough to establish ownership.
  if (text.includes('# /adjudicate — 审计后受理裁定')
      && text.includes('加载并严格按 `mini-adjudication` 技能执行')
      && groupScopes(scope).some((s) => [skillDir(s), skillDir(s).split(path.sep).join('/')]
        .some((dir) => text.includes(`\`${dir}\``)))) return;
  throw new Error(`An unmanaged command already exists; preserving it: ${file}`);
}
function syncCommand(scope) {
  assertCommandOwned(scope);
  const file = commandPath(scope);
  const receiptFile = commandReceiptPath(scope);
  const target = groupScopes(scope).find((s) => exists(path.join(skillDir(s), 'SKILL.md')) && exists(receiptPath(s)));
  if (!target) {
    if (exists(file)) fs.unlinkSync(file);
    if (exists(receiptFile)) fs.unlinkSync(receiptFile);
    return;
  }
  if (exists(file) && !exists(receiptFile)) {
    const backup = `${file}.legacy-backup-${crypto.randomUUID()}`;
    fs.copyFileSync(file, backup);
    console.log(`  retained legacy command backup ${backup}`);
  }
  const text = renderCommand(skillDir(target), skillDir(target));
  atomicWrite(file, text);
  atomicWrite(receiptFile, JSON.stringify({ schema_version: 1, target_scope: target, sha256: sha(text) }, null, 2) + '\n');
  console.log(`  command ${file} -> ${target}`);
}
function legacyInstallation(dest) {
  try {
    return readJson(path.join(dest, '_meta.json')).name === SKILL_NAME
      && /^name: mini-adjudication\s*$/m.test(fs.readFileSync(path.join(dest, 'SKILL.md'), 'utf8'));
  } catch { return false; }
}
function installPayload(scope, requestedLink) {
  const dest = skillDir(scope);
  const previous = readReceipt(scope);
  const present = exists(dest);
  const isLink = present && fs.lstatSync(dest).isSymbolicLink();
  const legacy = present && !previous;
  if (legacy && !legacyInstallation(dest)) throw new Error(`Unmanaged directory already exists; preserving it: ${dest}`);
  if (legacy) verifyManifest(dest);
  if (previous && ((previous.mode === 'link') !== isLink)) throw new Error(`Installation type changed outside the installer: ${dest}`);
  if (previous && isLink && fs.realpathSync(dest) !== previous.link_target) throw new Error(`Installation link changed outside the installer: ${dest}`);
  let link = requestedLink;
  if (link && (PKG_ROOT.split(path.sep).includes('node_modules')
      || !exists(path.join(PKG_ROOT, '.git')) || path.resolve(PKG_ROOT) === path.resolve(dest))) {
    console.log('  --link requires a separate Git checkout outside node_modules; copying instead');
    link = false;
  }
  const newFiles = payloadFiles(PKG_ROOT);
  if (present && !isLink) {
    for (const [relative, nextHash] of Object.entries(newFiles)) {
      const current = safeChild(dest, relative);
      if (exists(current) && (fs.lstatSync(current).isSymbolicLink() || !fs.lstatSync(current).isFile())) {
        throw new Error(`Managed file has an unexpected type; preserving it: ${current}`);
      }
      if (exists(current)) {
        const actual = sha(fs.readFileSync(current));
        if (previous && actual !== nextHash && actual !== previous.files[relative]) {
          throw new Error(`Local file changes would be overwritten; preserving them: ${current}`);
        }
      }
    }
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  const stage = fs.mkdtempSync(path.join(path.dirname(dest), `.${SKILL_NAME}-stage-`));
  const backup = `${dest}.backup-${crypto.randomUUID()}`;
  let movedOld = false;
  let movedStage = false;
  const oldReceipt = exists(receiptPath(scope)) ? fs.readFileSync(receiptPath(scope)) : null;
  try {
    if (link) {
      fs.rmdirSync(stage);
      try { fs.symlinkSync(PKG_ROOT, stage, process.platform === 'win32' ? 'junction' : 'dir'); }
      catch (error) {
        console.log(`  link failed (${error.code || error.message}); copying instead`);
        link = false;
        fs.mkdirSync(stage);
      }
    }
    if (!link) {
      // Keep unmanaged files. Delete obsolete owned files only when they
      // still have the bytes recorded by the previous installation.
      if (present && !isLink) fs.cpSync(dest, stage, { recursive: true, verbatimSymlinks: true });
      if (previous && !isLink) {
        for (const [relative, hash] of Object.entries(previous.files)) {
          const old = safeChild(stage, relative);
          if (!(relative in newFiles) && exists(old) && fs.lstatSync(old).isFile()
              && sha(fs.readFileSync(old)) === hash) fs.unlinkSync(old);
        }
      }
      fs.cpSync(PKG_ROOT, stage, {
        recursive: true,
        filter: (file) => !path.relative(PKG_ROOT, file) || isPayload(path.relative(PKG_ROOT, file)),
      });
    }
    verifyManifest(stage);
    for (const required of ['bin/cli.js', 'bin/python.js', 'runtime/validate_adjudication.py', 'cli/commands/adjudicate.md']) {
      if (!fs.statSync(safeChild(stage, required)).isFile()) throw new Error(`Package is missing ${required}`);
    }
    const retainBackup = legacy || (present && !isLink && link);
    if (present) { fs.renameSync(dest, backup); movedOld = true; }
    fs.renameSync(stage, dest); movedStage = true;
    atomicWrite(receiptPath(scope), JSON.stringify({
      schema_version: 1, scope, mode: link ? 'link' : 'copy', destination: dest,
      link_target: link ? fs.realpathSync(PKG_ROOT) : null,
      files: newFiles,
      ...(retainBackup ? { retained_backup: backup } : {}),
    }, null, 2) + '\n');
    if (movedOld && !retainBackup) {
      try { removePath(backup); }
      catch (error) { console.log(`  updated successfully; could not remove prior backup ${backup}: ${error.message}`); }
    }
    if (movedOld && retainBackup) console.log(`  retained previous installation ${backup}`);
    console.log(`  ${link ? 'linked' : 'copied'} ${dest}`);
  } catch (error) {
    if (movedStage) removePath(dest);
    if (movedOld && exists(backup)) fs.renameSync(backup, dest);
    if (oldReceipt) atomicWrite(receiptPath(scope), oldReceipt);
    else if (exists(receiptPath(scope))) fs.unlinkSync(receiptPath(scope));
    throw error;
  } finally { removePath(stage); }
}
function parseScopes(args) {
  const scopes = new Set();
  let link = false;
  for (const arg of args) {
    if (arg === '--all') SCOPES.forEach((scope) => scopes.add(scope));
    else if (arg === '--link') link = true;
    else if (SCOPES.includes(arg.slice(2)) && arg.startsWith('--')) scopes.add(arg.slice(2));
    else throw new Error(`Unknown option: ${arg}`);
  }
  return { scopes: scopes.size ? [...scopes] : ['user'], link };
}
function cmdInstall(args) {
  const { scopes, link } = parseScopes(args);
  verifyManifest(PKG_ROOT);
  scopes.forEach(assertCommandOwned);
  console.log(`Installing ${SKILL_NAME} (${scopes.join(', ')}):`);
  for (const scope of scopes) installPayload(scope, link);
  for (const scope of new Set(scopes.map((s) => s === 'claude' ? 'claude' : 'user'))) syncCommand(scope);
  console.log(`\nDone. Open a new agent session, then: /adjudicate <findings.json>\n${HOOK_NOTICE}`);
  return 0;
}
function pruneEmpty(dir) {
  if (!exists(dir) || !fs.lstatSync(dir).isDirectory()) return;
  for (const entry of fs.readdirSync(dir)) {
    const child = path.join(dir, entry);
    if (fs.lstatSync(child).isDirectory() && !fs.lstatSync(child).isSymbolicLink()) pruneEmpty(child);
  }
  if (!fs.readdirSync(dir).length) fs.rmdirSync(dir);
}
function cmdUninstall(args) {
  const { scopes, link } = parseScopes(args);
  if (link) throw new Error('--link applies only to install/update');
  scopes.forEach(assertCommandOwned);
  for (const scope of scopes) {
    const dest = skillDir(scope);
    const receipt = readReceipt(scope);
    if (!receipt) {
      if (exists(dest)) throw new Error(`No ownership receipt; preserving ${dest}. Reinstall first to migrate this installation.`);
      continue;
    }
    if (exists(dest)) {
      if (receipt.mode === 'link') {
        if (!fs.lstatSync(dest).isSymbolicLink()
            || (fs.existsSync(dest) && fs.realpathSync(dest) !== receipt.link_target)) {
          throw new Error(`Installation link changed outside the installer; preserving ${dest}`);
        }
        fs.unlinkSync(dest);
      } else {
        if (fs.lstatSync(dest).isSymbolicLink()) throw new Error(`Installation type changed; preserving ${dest}`);
        for (const [relative, hash] of Object.entries(receipt.files)) {
          const file = safeChild(dest, relative);
          if (exists(file) && fs.lstatSync(file).isFile() && !fs.lstatSync(file).isSymbolicLink()
              && sha(fs.readFileSync(file)) === hash) fs.unlinkSync(file);
        }
        pruneEmpty(dest);
        if (exists(dest)) console.log(`  preserved local or modified files in ${dest}`);
      }
    }
    fs.unlinkSync(receiptPath(scope));
    console.log(`  removed managed installation (${scope})`);
  }
  for (const scope of new Set(scopes.map((s) => s === 'claude' ? 'claude' : 'user'))) syncCommand(scope);
  return 0;
}
function runCheck(python, script, args, label, failures) {
  const result = spawnSync(python.command, [...python.prefix, script, ...args], {
    encoding: 'utf8', timeout: 120000, maxBuffer: 8 * 1024 * 1024, windowsHide: true,
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
  });
  const ok = !result.error && result.status === 0;
  console.log(`  ${ok ? 'PASS' : 'FAIL'} ${label}`);
  if (!ok) {
    failures.push(label);
    const detail = result.error ? result.error.message : `${result.stdout || ''}${result.stderr || ''}`;
    const lines = detail.trim().split('\n');
    const shown = lines.length <= 30 ? lines : [...lines.slice(0, 6), '…', ...lines.slice(-23)];
    console.log(shown.map((line) => `       ${line}`).join('\n'));
  }
}
function cmdDoctor(args) {
  if (args.some((arg) => arg !== '--full')) throw new Error('doctor accepts only --full');
  const full = args.includes('--full');
  const scopes = SCOPES.filter((scope) => exists(path.join(skillDir(scope), 'SKILL.md')) || exists(receiptPath(scope)));
  const failures = [];
  function fail(message) { failures.push(message); console.log(`  FAIL ${message}`); }
  console.log('mini-adjudication doctor:');
  if (!scopes.length) fail('No installation found (run: mini-adjudication install)');
  const python = findPython();
  if (!python) fail('Python 3.10+ unavailable; install it or set MINI_ADJUDICATION_PYTHON');
  else console.log(`  PASS Python ${python.version} (${python.command})`);
  const rg = spawnSync('rg', ['--version'], { encoding: 'utf8', timeout: 10000, windowsHide: true });
  if (rg.error || rg.status !== 0) fail('ripgrep (rg) is required for reproducible search evidence');
  else console.log('  PASS ripgrep available');
  for (const scope of scopes) {
    const dest = skillDir(scope);
    try {
      const receipt = readReceipt(scope);
      if (!receipt) throw new Error(`Missing installation receipt (${scope}); reinstall to migrate`);
      if (!exists(dest)) throw new Error(`Missing skill directory (${scope})`);
      if (receipt.mode === 'link') {
        if (!fs.lstatSync(dest).isSymbolicLink() || fs.realpathSync(dest) !== receipt.link_target) {
          throw new Error(`Invalid installation link (${scope})`);
        }
      } else {
        if (fs.lstatSync(dest).isSymbolicLink()) throw new Error(`Unexpected installation link (${scope})`);
        for (const [relative, hash] of Object.entries(receipt.files)) {
          const file = safeChild(dest, relative);
          if (!exists(file) || !fs.lstatSync(file).isFile() || fs.lstatSync(file).isSymbolicLink()
              || sha(fs.readFileSync(file)) !== hash) throw new Error(`Installed file changed or missing (${scope}): ${relative}`);
        }
      }
      verifyManifest(dest);
      console.log(`  PASS installed files and manifest (${scope})`);
      if (python) {
        const fixture = path.join(dest, 'fixtures', 'mini-adjudication', 'expected');
        runCheck(python, path.join(dest, 'runtime', full ? 'regression.py' : 'validate_adjudication.py'),
          full ? [] : [path.join(fixture, 'adjudication-notes.md'), '--evidence-ledger', path.join(fixture, 'evidence.jsonl')],
          `${full ? 'full regression' : 'fixture validation'} (${scope})`, failures);
      }
    } catch (error) { fail(error.message); }
  }
  for (const scope of new Set(scopes.map((s) => s === 'claude' ? 'claude' : 'user'))) {
    try {
      const file = commandPath(scope);
      if (!exists(file)) throw new Error(`Missing trigger command: ${file}`);
      assertCommandOwned(scope);
      const receipt = readJson(commandReceiptPath(scope));
      const target = receipt.target_scope;
      if (!groupScopes(scope).includes(target) || !exists(receiptPath(target))
          || !exists(path.join(skillDir(target), 'bin', 'cli.js'))
          || fs.readFileSync(file, 'utf8') !== renderCommand(skillDir(target), skillDir(target))) {
        throw new Error(`Invalid trigger command target or content: ${file}`);
      }
      console.log(`  PASS trigger command (${target}): ${file}`);
    } catch (error) { fail(error.message); }
  }
  console.log(`  INFO ${HOOK_NOTICE}`);
  console.log(failures.length ? `\nFAIL: ${failures.length} check(s) failed` : '\nOK: all requested checks passed');
  return failures.length ? 1 : 0;
}
function cmdRun(args) {
  const [name, ...scriptArgs] = args;
  if (!name || !/^[a-z][a-z0-9_]*(?:\.py)?$/.test(name)) throw new Error('Usage: mini-adjudication run <runtime-script.py> [args...]');
  const script = path.join(PKG_ROOT, 'runtime', name.endsWith('.py') ? name : `${name}.py`);
  if (!fs.existsSync(script)) throw new Error(`Unknown runtime script: ${name}`);
  const python = requirePython();
  const result = spawnSync(python.command, [...python.prefix, script, ...scriptArgs], {
    stdio: 'inherit', windowsHide: true, env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
  });
  if (result.error) throw result.error;
  return result.status ?? 1;
}
function help() {
  console.log(`mini-adjudication — adjudicate existing vulnerability findings

Usage:
  mini-adjudication install [--user|--zcode|--claude|--all] [--link]
  mini-adjudication update  [same options as install]
  mini-adjudication uninstall [--user|--zcode|--claude|--all]
  mini-adjudication doctor [--full]
  mini-adjudication run <runtime-script.py> [args...]

Default scope: --user (~/.agents/skills and ~/.zcode/commands).
--zcode uses ~/.zcode/skills; --claude uses ~/.claude/skills and commands.
--link links a separate Git checkout; other sources fall back to a copy.
Updates stage and validate files before replacement; uninstall preserves
unmanaged or modified files. Legacy installations retain a migration backup.
Runtime commands require Python >=3.10 and search evidence requires ripgrep.
Set MINI_ADJUDICATION_PYTHON to choose a Python executable explicitly.
doctor checks installed files, the fixture and command; --full adds regression.
${HOOK_NOTICE}`);
}
function main(argv = process.argv.slice(2)) {
  const [command, ...args] = argv;
  switch (command) {
    case 'install': case 'update': return cmdInstall(args);
    case 'uninstall': return cmdUninstall(args);
    case 'doctor': return cmdDoctor(args);
    case 'run': return cmdRun(args);
    case 'help': case '--help': case '-h': case undefined: help(); return 0;
    default: throw new Error(`Unknown command: ${command}`);
  }
}
if (require.main === module) {
  try { process.exitCode = main(); }
  catch (error) { console.error(`FAIL: ${error.message}`); process.exitCode = 1; }
}
module.exports = { main, renderCommand, payloadFiles, verifyManifest, shellQuote };
