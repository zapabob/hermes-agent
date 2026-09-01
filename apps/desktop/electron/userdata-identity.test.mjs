import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const MAIN_SOURCE = fs.readFileSync(path.join(HERE, 'main.ts'), 'utf8')

test('pins the stable Hermes application name before resolving userData', () => {
  const setNameIndex = MAIN_SOURCE.search(/^[ \t]*app\.setName\(APP_NAME\)[ \t]*$/m)
  const firstUserDataIndex = MAIN_SOURCE.search(/^[ \t]*const .+app\.getPath\('userData'\)/m)

  assert.notEqual(setNameIndex, -1)
  assert.notEqual(firstUserDataIndex, -1)
  assert.ok(
    setNameIndex < firstUserDataIndex,
    'the application name must be fixed before Electron derives the userData directory'
  )
})
