<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { api } from '../lib/api.js'
import {
  COLUMNS,
  FILTER_EXTENSIONS,
  VARIANT_SORT_ATTRIBUTE,
  nextOrder,
  previewKind,
  sortAndFilter,
} from '../lib/variant.js'
import PreviewModal from './PreviewModal.vue'
import SyncPanel from './SyncPanel.vue'

defineProps({ username: String })
const emit = defineEmits(['logout'])

const files = ref([])
const status = ref('')
const error = ref('')
const selectedId = ref(null)
const previewFile = ref(null)
const dragging = ref(false)
const columnsOpen = ref(false)
const visible = reactive(Object.fromEntries(COLUMNS.map((c) => [c.key, true])))
const sort = reactive({ attribute: VARIANT_SORT_ATTRIBUTE, order: 'none' })
const typeFilter = ref('all')
const fileInput = ref(null)
const dropdown = ref(null)

function closeMenu(e) {
  if (columnsOpen.value && dropdown.value && !dropdown.value.contains(e.target)) columnsOpen.value = false
}

const displayed = computed(() =>
  sortAndFilter(files.value, { extension: typeFilter.value, attribute: sort.attribute, order: sort.order }),
)
const visibleColumns = computed(() => COLUMNS.filter((c) => visible[c.key]))
const selected = computed(() => files.value.find((f) => f.id === selectedId.value) || null)

const fmtDate = (iso) => new Date(iso).toLocaleString('uk-UA')
const fmtSize = (n) => (n < 1024 ? `${n} Б` : n < 1048576 ? `${(n / 1024).toFixed(1)} КБ` : `${(n / 1048576).toFixed(1)} МБ`)
const cell = (f, key) => (key.endsWith('_at') ? fmtDate(f[key]) : key === 'size' ? fmtSize(f.size) : f[key])

async function refresh() {
  try {
    files.value = await api.listFiles()
    error.value = ''
    status.value = `Файлів у папці: ${files.value.length}`
  } catch (e) {
    handle(e)
  }
}

function handle(e) {
  error.value = e.message
  if (e.status === 401) emit('logout')
}

function headerClick(key) {
  if (sort.attribute !== key) {
    sort.attribute = key
    sort.order = 'asc'
  } else sort.order = nextOrder(sort.order)
}

const variantOrder = computed({
  get: () => (sort.attribute === VARIANT_SORT_ATTRIBUTE ? sort.order : 'none'),
  set: (v) => {
    sort.attribute = VARIANT_SORT_ATTRIBUTE
    sort.order = v
  },
})

function arrow(key) {
  if (sort.attribute !== key) return ''
  return { asc: ' ▲', desc: ' ▼', none: '' }[sort.order]
}

function setAll(on) {
  COLUMNS.forEach((c) => c.hideable && (visible[c.key] = on))
}

function rowClick(f) {
  selectedId.value = f.id
  previewFile.value = f
}

async function uploadFiles(list) {
  const items = [...list]
  if (!items.length) return
  let ok = 0
  for (const file of items) {
    try {
      status.value = `Вивантаження «${file.name}»…`
      await api.upload(file)
      ok++
    } catch (e) {
      handle(e)
    }
  }
  await refresh()
  status.value = `Вивантажено файлів: ${ok}`
}

function onPick(e) {
  uploadFiles(e.target.files)
  e.target.value = ''
}

function onDrop(e) {
  dragging.value = false
  uploadFiles(e.dataTransfer.files)
}

async function download() {
  const f = selected.value
  if (!f) return
  try {
    const blob = await api.download(f.id)
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = f.name
    a.click()
    setTimeout(() => URL.revokeObjectURL(a.href), 1000)
    status.value = `Завантажено: ${f.name}`
  } catch (e) {
    handle(e)
  }
}

async function remove() {
  const f = selected.value
  if (!f || !confirm(`Видалити файл «${f.name}» з віддаленої папки?`)) return
  try {
    await api.remove(f.id)
    selectedId.value = null
    await refresh()
    status.value = `Видалено: ${f.name}`
  } catch (e) {
    handle(e)
  }
}

onMounted(() => {
  refresh()
  document.addEventListener('click', closeMenu)
})
onBeforeUnmount(() => document.removeEventListener('click', closeMenu))
</script>

<template>
  <div class="layout" @dragover.prevent="dragging = true">
    <header class="topbar">
      <span class="brand">Хмарне сховище</span>
      <span class="spacer" />
      <span class="user">Користувач: <strong>{{ username }}</strong></span>
      <button @click="emit('logout')">Вийти</button>
    </header>

    <nav class="toolbar">
      <button @click="refresh">Оновити</button>
      <button class="primary" @click="fileInput.click()">Вивантажити…</button>
      <input ref="fileInput" type="file" multiple hidden @change="onPick" />
      <button :disabled="!selected" @click="download">Завантажити</button>
      <button :disabled="!selected" class="danger" @click="remove">Видалити</button>
      <span class="sep" />
      <div ref="dropdown" class="dropdown">
        <button @click="columnsOpen = !columnsOpen">Стовпці ▾</button>
        <div v-if="columnsOpen" class="menu">
          <label v-for="c in COLUMNS" :key="c.key" :class="{ disabled: !c.hideable }">
            <input v-model="visible[c.key]" type="checkbox" :disabled="!c.hideable" /> {{ c.title }}
          </label>
          <hr />
          <button class="link" @click="setAll(true)">Показати всі</button>
          <button class="link" @click="setAll(false)">Приховати всі, крім імені</button>
        </div>
      </div>
      <label>
        Фільтр:
        <select v-model="typeFilter">
          <option value="all">Усі файли</option>
          <option v-for="ext in FILTER_EXTENSIONS" :key="ext" :value="ext">Лише {{ ext }}</option>
        </select>
      </label>
      <label>
        Сортування за датою зміни:
        <select v-model="variantOrder">
          <option value="none">без сортування</option>
          <option value="asc">за зростанням ▲</option>
          <option value="desc">за спаданням ▼</option>
        </select>
      </label>
    </nav>

    <p v-if="error" class="error banner">{{ error }}</p>

    <section class="table-wrap">
      <table>
        <thead>
          <tr>
            <th v-for="c in visibleColumns" :key="c.key" :class="{ num: c.key === 'size' }" @click="headerClick(c.key)">{{ c.title }}{{ arrow(c.key) }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="f in displayed"
            :key="f.id"
            :class="{ selected: f.id === selectedId }"
            @click="rowClick(f)"
          >
            <td v-for="c in visibleColumns" :key="c.key" :class="{ num: c.key === 'size' }">
              <template v-if="c.key === 'name'">
                <span class="badge" :class="previewKind(f.name)">{{ f.extension || '—' }}</span> {{ f.name }}
              </template>
              <template v-else>{{ cell(f, c.key) }}</template>
            </td>
          </tr>
          <tr v-if="!displayed.length">
            <td :colspan="visibleColumns.length" class="empty">Немає файлів. Перетягніть файли сюди, щоб вивантажити.</td>
          </tr>
        </tbody>
      </table>
    </section>

    <p class="muted hint">Клік по рядку — перегляд (.xml як текст, .png як зображення). Перетягніть файли у вікно для вивантаження.</p>

    <SyncPanel :username="username" @changed="refresh" />

    <footer class="status">{{ status }}</footer>

    <div v-if="dragging" class="dropzone" @dragleave.self="dragging = false" @drop.prevent="onDrop">
      <div>Відпустіть файли для вивантаження</div>
    </div>

    <PreviewModal v-if="previewFile" :file="previewFile" @close="previewFile = null" />
  </div>
</template>
