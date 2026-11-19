// Тристороннє узгодження папки (дзеркало cloudfolder/core/sync.py) +
// виконання через File System Access API (Chromium: Chrome / Edge).

export const STATE_FILE_NAME = '.cloudfolder-sync.json'

export function conflictCopyName(name, suffix = 'конфлікт') {
  const dot = name.lastIndexOf('.')
  return dot > 0 ? `${name.slice(0, dot)} (${suffix})${name.slice(dot)}` : `${name} (${suffix})`
}

/** local/remote/base: { name: sha256 } -> [{kind, name}] */
export function planSync(local, remote, base) {
  const names = [...new Set([...Object.keys(local), ...Object.keys(remote), ...Object.keys(base)])].sort()
  const actions = []
  for (const name of names) {
    const l = local[name]
    const r = remote[name]
    const b = base[name]
    if (l === r) continue
    let kind
    if (b === undefined) {
      kind = r === undefined ? 'upload' : l === undefined ? 'download' : 'conflict'
    } else {
      const lc = l !== b
      const rc = r !== b
      if (lc && !rc) kind = l === undefined ? 'delete_remote' : 'upload'
      else if (rc && !lc) kind = r === undefined ? 'delete_local' : 'download'
      else if (l === undefined) kind = 'download'
      else if (r === undefined) kind = 'upload'
      else kind = 'conflict'
    }
    actions.push({ kind, name })
  }
  return actions
}

export async function sha256Hex(buffer) {
  const digest = await crypto.subtle.digest('SHA-256', buffer)
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

export const syncSupported = () => typeof window !== 'undefined' && 'showDirectoryPicker' in window

async function scan(dir) {
  const manifest = {}
  for await (const [name, handle] of dir.entries()) {
    if (handle.kind !== 'file' || name.startsWith('.')) continue
    const file = await handle.getFile()
    manifest[name] = await sha256Hex(await file.arrayBuffer())
  }
  return manifest
}

async function readBase(dir, account) {
  try {
    const file = await (await dir.getFileHandle(STATE_FILE_NAME)).getFile()
    const data = JSON.parse(await file.text())
    return data.account === account ? data.files || {} : {}
  } catch {
    return {}
  }
}

async function writeFile(dir, name, data) {
  const handle = await dir.getFileHandle(name, { create: true })
  const w = await handle.createWritable()
  await w.write(data)
  await w.close()
}

/** Виконує один цикл синхронізації; api — об'єкт з lib/api.js */
export async function runSync(dir, api, account) {
  const local = await scan(dir)
  const remoteList = await api.listFiles()
  const remoteByName = Object.fromEntries(remoteList.map((f) => [f.name, f]))
  const remote = Object.fromEntries(remoteList.map((f) => [f.name, f.sha256]))
  const base = await readBase(dir, account)
  const plan = planSync(local, remote, base)
  const newBase = Object.fromEntries(Object.entries(local).filter(([n, h]) => remote[n] === h))
  const done = []
  const errors = []
  for (const action of plan) {
    const { kind, name } = action
    try {
      if (kind === 'upload') {
        const file = await (await dir.getFileHandle(name)).getFile()
        newBase[name] = (await api.upload(file, name)).sha256
      } else if (kind === 'download') {
        const blob = await api.download(remoteByName[name].id)
        await writeFile(dir, name, blob)
        newBase[name] = await sha256Hex(await blob.arrayBuffer())
      } else if (kind === 'delete_remote') {
        await api.remove(remoteByName[name].id)
        delete newBase[name]
      } else if (kind === 'delete_local') {
        await dir.removeEntry(name)
        delete newBase[name]
      } else if (kind === 'conflict') {
        const copy = conflictCopyName(name)
        const localFile = await (await dir.getFileHandle(name)).getFile()
        await writeFile(dir, copy, localFile)
        newBase[copy] = (await api.upload(localFile, copy)).sha256
        const blob = await api.download(remoteByName[name].id)
        await writeFile(dir, name, blob)
        newBase[name] = await sha256Hex(await blob.arrayBuffer())
      }
      done.push(action)
    } catch (e) {
      errors.push(`${kind}: ${name} — ${e.message}`)
      if (base[name] !== undefined) newBase[name] = base[name]
    }
  }
  await writeFile(dir, STATE_FILE_NAME, JSON.stringify({ account, files: newBase }, null, 2))
  return { actions: done, errors }
}
