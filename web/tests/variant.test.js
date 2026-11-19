import { describe, expect, it } from 'vitest'
import { filterFiles, nextOrder, previewKind, sortAndFilter, sortFiles } from '../src/lib/variant.js'

const at = (min) => new Date(Date.UTC(2026, 10, 1, 12, min)).toISOString()
const FILES = [
  { id: 1, name: 'Main.java', modified_at: at(30) },
  { id: 2, name: 'logo.png', modified_at: at(10) },
  { id: 3, name: 'config.xml', modified_at: at(50) },
  { id: 4, name: 'notes.txt', modified_at: at(20) },
  { id: 5, name: 'Util.JAVA', modified_at: at(40) },
]
const names = (fs) => fs.map((f) => f.name)

describe('варіант 12: сортування за датою модифікації', () => {
  it('за зростанням', () => {
    expect(names(sortFiles(FILES, 'modified_at', 'asc'))).toEqual([
      'logo.png', 'notes.txt', 'Main.java', 'Util.JAVA', 'config.xml',
    ])
  })
  it('за спаданням', () => {
    expect(names(sortFiles(FILES, 'modified_at', 'desc'))).toEqual([
      'config.xml', 'Util.JAVA', 'Main.java', 'notes.txt', 'logo.png',
    ])
  })
  it('none зберігає порядок і не мутує вхід', () => {
    const copy = [...FILES]
    sortFiles(FILES, 'modified_at', 'desc')
    expect(FILES).toEqual(copy)
    expect(names(sortFiles(FILES, 'modified_at', 'none'))).toEqual(names(FILES))
  })
  it('цикл none → asc → desc → none', () => {
    expect([nextOrder('none'), nextOrder('asc'), nextOrder('desc')]).toEqual(['asc', 'desc', 'none'])
  })
})

describe('варіант 12: фільтр усі / .java / .png', () => {
  it('усі файли', () => expect(filterFiles(FILES, 'all')).toHaveLength(5))
  it('.java без урахування регістру', () => expect(names(filterFiles(FILES, '.java'))).toEqual(['Main.java', 'Util.JAVA']))
  it('.png', () => expect(names(filterFiles(FILES, 'png'))).toEqual(['logo.png']))
  it('тип поза варіантом — помилка', () => expect(() => filterFiles(FILES, '.xml')).toThrow())
  it('фільтр + сортування разом', () => {
    expect(names(sortAndFilter(FILES, { extension: '.java', order: 'desc' }))).toEqual(['Util.JAVA', 'Main.java'])
  })
})

describe('перегляд вмісту', () => {
  it('.xml — текст, .png — зображення, решта — ні', () => {
    expect(previewKind('a.XML')).toBe('text')
    expect(previewKind('b.png')).toBe('image')
    expect(previewKind('c.java')).toBe('none')
  })
})
