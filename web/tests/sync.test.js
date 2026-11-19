import { describe, expect, it } from 'vitest'
import { conflictCopyName, planSync, sha256Hex } from '../src/lib/sync.js'

const kinds = (plan) => Object.fromEntries(plan.map((a) => [a.name, a.kind]))

describe('planSync (ідентичний алгоритму десктоп-клієнта)', () => {
  it('перша синхронізація', () => {
    expect(kinds(planSync({ a: '1' }, { b: '2' }, {}))).toEqual({ a: 'upload', b: 'download' })
  })
  it('редагування та видалення з обох боків', () => {
    const plan = planSync({ a: 'L', c: '1' }, { b: 'R', c: '1' }, { a: '1', b: '1', c: '1', d: '1' })
    expect(kinds(plan)).toEqual({ a: 'upload', b: 'download' })
    expect(kinds(planSync({ b: '1' }, { a: '1' }, { a: '1', b: '1' }))).toEqual({
      a: 'delete_remote',
      b: 'delete_local',
    })
  })
  it('конфлікт', () => {
    expect(planSync({ a: 'L' }, { a: 'R' }, { a: '1' })).toEqual([{ kind: 'conflict', name: 'a' }])
    expect(conflictCopyName('doc.xml')).toBe('doc (конфлікт).xml')
  })
  it('sha256 збігається з Python hashlib', async () => {
    const hex = await sha256Hex(new TextEncoder().encode('abc'))
    expect(hex).toBe('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
  })
})
