'use strict'
// Builds the installed-app folder: dist/shell/AssignmentMonitor/ (AssignmentMonitor.exe plus resources/{ui,engine,assets}).
// Run from desktop/ after `npm run build` in ui/ and `python build_engine.py` in the repository root.
//   node scripts/package.cjs            build the folder
// Inno Setup (installer.iss) then wraps that folder into AssignmentMonitor-Setup.exe.
const fs = require('node:fs')
const path = require('node:path')
const { packager } = require('@electron/packager')
const { FuseV1Options, FuseVersion, flipFuses } = require('@electron/fuses')

const ROOT = path.resolve(__dirname, '..', '..')
const OUT = path.join(ROOT, 'dist', 'shell')
const NAME = 'AssignmentMonitor'
const version = /APP_VERSION\s*=\s*"([^"]+)"/.exec(fs.readFileSync(path.join(ROOT, 'config.py'), 'utf8'))?.[1]
if (!version) throw new Error('APP_VERSION not found in config.py')

const need = [[path.join(ROOT, 'ui', 'dist', 'index.html'), 'run `npm run build` in ui/'],
  [path.join(ROOT, 'dist', 'engine', 'AssignmentEngine', 'AssignmentEngine.exe'), 'run `python build_engine.py`']]
for (const [file, hint] of need) if (!fs.existsSync(file)) throw new Error(`Missing ${file}: ${hint}`)

async function main() {
  fs.rmSync(path.join(OUT, NAME), { recursive: true, force: true })
  const [built] = await packager({
    dir: path.resolve(__dirname, '..'), out: OUT, name: NAME, platform: 'win32', arch: 'x64', overwrite: true, asar: true, prune: true,
    appVersion: version, icon: path.join(ROOT, 'assets', 'icon.ico'),
    ignore: [/^\/test($|\/)/, /^\/scripts($|\/)/, /^\/README\.md$/, /^\/dist($|\/)/, /\.map$/],
    win32metadata: { CompanyName: 'Nobody243', ProductName: 'Assignment Monitor', FileDescription: 'Assignment Monitor', OriginalFilename: `${NAME}.exe` },
  })
  const target = path.join(OUT, NAME)
  fs.rmSync(target, { recursive: true, force: true })
  fs.renameSync(built, target)
  const res = path.join(target, 'resources')
  fs.cpSync(path.join(ROOT, 'ui', 'dist'), path.join(res, 'ui'), { recursive: true })
  fs.cpSync(path.join(ROOT, 'dist', 'engine', 'AssignmentEngine'), path.join(res, 'engine'), { recursive: true })
  fs.cpSync(path.join(ROOT, 'assets'), path.join(res, 'assets'), { recursive: true })

  // switch off the Electron features this app never uses, so they cannot be turned on against it
  await flipFuses(path.join(target, `${NAME}.exe`), {
    version: FuseVersion.V1,
    [FuseV1Options.RunAsNode]: false,
    [FuseV1Options.EnableNodeOptionsEnvironmentVariable]: false,
    [FuseV1Options.EnableNodeCliInspectArguments]: false,
    [FuseV1Options.EnableEmbeddedAsarIntegrityValidation]: true,
    [FuseV1Options.OnlyLoadAppFromAsar]: true,
    [FuseV1Options.GrantFileProtocolExtraPrivileges]: false,
  })
  console.log(`Shell: ${target} (version ${version})`)
}
main().catch(e => { console.error(e); process.exit(1) })
