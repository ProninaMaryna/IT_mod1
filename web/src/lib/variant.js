// Операції варіанта 12 (дзеркало cloudfolder/core/variant.py).
// Перегляд: .xml — текст, .png — зображення.
// Сортування: дата і час модифікації ▲/▼; фільтр: усі / .java / .png (операція №2).

export const PREVIEW_TEXT = ['.xml']
export const PREVIEW_IMAGE = ['.png']
export const FILTER_EXTENSIONS = ['.java', '.png']
export const VARIANT_SORT_ATTRIBUTE = 'modified_at'

export const COLUMNS = [
  { key: 'name', title: "Ім'я", hideable: false },
  { key: 'created_at', title: 'Створено', hideable: true },
  { key: 'modified_at', title: 'Змінено', hideable: true },
  { key: 'uploaded_by', title: 'Вивантажив', hideable: true },
  { key: 'edited_by', title: 'Редагував', hideable: true },
  { key: 'size', title: 'Розмір', hideable: true },
]

export function extensionOf(name) {
  const dot = name.lastIndexOf('.')
  return dot > 0 ? name.slice(dot).toLowerCase() : ''
}

export function previewKind(name) {
  const ext = extensionOf(name)
  if (PREVIEW_TEXT.includes(ext)) return 'text'
  if (PREVIEW_IMAGE.includes(ext)) return 'image'
  return 'none'
}

export function nextOrder(order) {
  return { none: 'asc', asc: 'desc', desc: 'none' }[order]
}

function compare(a, b, attribute) {
  let x = a[attribute]
  let y = b[attribute]
  if (attribute.endsWith('_at')) {
    x = Date.parse(x)
    y = Date.parse(y)
  } else if (typeof x !== 'number') {
    x = String(x).toLocaleLowerCase('uk')
    y = String(y).toLocaleLowerCase('uk')
  }
  if (x < y) return -1
  if (x > y) return 1
  return a.name.toLocaleLowerCase('uk').localeCompare(b.name.toLocaleLowerCase('uk'))
}

export function sortFiles(files, attribute = VARIANT_SORT_ATTRIBUTE, order = 'asc') {
  const items = [...files]
  if (order === 'none') return items
  const sign = order === 'desc' ? -1 : 1
  return items.sort((a, b) => sign * compare(a, b, attribute))
}

export function filterFiles(files, extension = 'all') {
  if (!extension || extension === 'all') return [...files]
  const ext = extension.startsWith('.') ? extension.toLowerCase() : '.' + extension.toLowerCase()
  if (!FILTER_EXTENSIONS.includes(ext)) throw new Error(`Тип ${ext} не передбачено варіантом`)
  return files.filter((f) => extensionOf(f.name) === ext)
}

export function sortAndFilter(files, { extension = 'all', attribute = VARIANT_SORT_ATTRIBUTE, order = 'none' } = {}) {
  return sortFiles(filterFiles(files, extension), attribute, order)
}
