// Resolve electronDist at runtime (#38673, #47917): electron-builder 26.8.x can
// re-unpack a broken Electron.app; reusing the installed dist dodges that.
// npm workspace hoisting is non-deterministic — require.resolve finds electron
// wherever it landed. Dist present → -c.electronDist=<abs>/dist; absent → let
// electron-builder fetch via @electron/get (electronVersion + ELECTRON_MIRROR).

import fs from "node:fs"
import path from "node:path"
import { spawnSync } from "node:child_process"
import { createRequire } from "node:module"
import { pathToFileURL } from "node:url"

const require = createRequire(import.meta.url)

function electronDistDir() {
  try {
    return path.join(path.dirname(require.resolve("electron/package.json")), "dist")
  } catch {
    return null
  }
}

function distBinary(dist) {
  if (process.platform === "darwin") {
    return path.join(dist, "Electron.app", "Contents", "MacOS", "Electron")
  }
  if (process.platform === "win32") {
    return path.join(dist, "electron.exe")
  }
  return path.join(dist, "electron")
}

function electronBuilderCli() {
  const pkgJson = require.resolve("electron-builder/package.json")
  const bin = require(pkgJson).bin
  const rel = typeof bin === "string" ? bin : bin["electron-builder"]
  return path.join(path.dirname(pkgJson), rel)
}

export function normalizeLocalBuildArgs(forwardedArgs, dist = null) {
  const args = []
  for (let index = 0; index < forwardedArgs.length; index += 1) {
    const arg = forwardedArgs[index]
    if (arg === "--publish" || arg === "-p") {
      index += 1
      continue
    }
    if (arg.startsWith("--publish=") || arg.startsWith("-p=")) continue
    args.push(arg)
  }
  if (dist) args.push(`-c.electronDist=${dist}`)
  // Repeating this yargs option turns it into an array, which can make
  // electron-builder enter its implicit CI publish path.
  args.push("--publish=never")
  return args
}

function main() {
  const dist = electronDistDir()
  const usableDist = dist && fs.existsSync(distBinary(dist)) ? dist : null
  if (!usableDist) {
    console.warn(
      "[run-electron-builder] no local electron dist; electron-builder will fetch " +
        "via @electron/get (electronVersion + ELECTRON_MIRROR)."
    )
  }
  const args = normalizeLocalBuildArgs(process.argv.slice(2), usableDist)
  const result = spawnSync(process.execPath, [electronBuilderCli(), ...args], {
    stdio: "inherit",
  })
  if (result.error) {
    console.error(`[run-electron-builder] spawn failed: ${result.error.message}`)
    process.exit(1)
  }
  process.exit(result.status == null ? 1 : result.status)
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main()
}
