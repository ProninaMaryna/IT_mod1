<script setup>
import { ref, onBeforeUnmount } from 'vue'
import { api } from '../lib/api.js'
import { runSync, syncSupported } from '../lib/sync.js'

const props = defineProps({ username: String })
const emit = defineEmits(['changed'])
const supported = syncSupported()
const dir = ref(null)
const auto = ref(false)
const busy = ref(false)
const log = ref([])
let timer = null

const labels = {
  upload: 'вивантажено',
  download: 'завантажено',
  delete_remote: 'видалено на сервері',
  delete_local: 'видалено локально',
  conflict: 'конфлікт (збережено обидві версії)',
}

async function choose() {
  try {
    dir.value = await window.showDirectoryPicker({ mode: 'readwrite' })
    await syncNow()
  } catch (e) {
    if (e.name !== 'AbortError') log.value.unshift(`Помилка: ${e.message}`)
  }
}

async function syncNow() {
  if (!dir.value || busy.value) return
  busy.value = true
  const stamp = new Date().toLocaleTimeString('uk-UA')
  try {
    const { actions, errors } = await runSync(dir.value, api, props.username)
    const lines = actions.map((a) => `    ${labels[a.kind]}: ${a.name}`)
    errors.forEach((e) => lines.push(`    ПОМИЛКА ${e}`))
    log.value.unshift(...[`[${stamp}] ${actions.length ? `змін: ${actions.length}` : 'змін немає'}`, ...lines])
    if (actions.length) emit('changed')
  } catch (e) {
    log.value.unshift(`[${stamp}] Помилка: ${e.message}`)
  } finally {
    busy.value = false
  }
}

function toggleAuto() {
  clearInterval(timer)
  if (auto.value) timer = setInterval(syncNow, 10000)
}
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <section class="sync">
    <h2>Синхронізація локальної папки</h2>
    <p v-if="!supported" class="muted">
      Браузер не підтримує File System Access API — синхронізація доступна в Chrome/Edge або в десктоп-клієнті.
    </p>
    <div v-else class="sync-row">
      <button @click="choose">{{ dir ? `Папка: ${dir.name}` : 'Обрати папку…' }}</button>
      <button class="primary" :disabled="!dir || busy" @click="syncNow">Синхронізувати зараз</button>
      <label class="check"><input v-model="auto" type="checkbox" :disabled="!dir" @change="toggleAuto" /> кожні 10 с</label>
    </div>
    <pre v-if="log.length" class="log">{{ log.slice(0, 40).join('\n') }}</pre>
  </section>
</template>
