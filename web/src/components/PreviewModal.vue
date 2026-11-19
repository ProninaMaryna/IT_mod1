<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { api } from '../lib/api.js'
import { previewKind } from '../lib/variant.js'

const props = defineProps({ file: Object })
const emit = defineEmits(['close'])
const text = ref('')
const imageUrl = ref('')
const error = ref('')
const loading = ref(false)

function cleanup() {
  if (imageUrl.value) URL.revokeObjectURL(imageUrl.value)
  imageUrl.value = ''
  text.value = ''
}

watch(
  () => props.file,
  async (file) => {
    cleanup()
    error.value = ''
    if (!file || previewKind(file.name) === 'none') return
    loading.value = true
    try {
      const blob = await api.download(file.id)
      if (previewKind(file.name) === 'text') text.value = await blob.text()
      else imageUrl.value = URL.createObjectURL(blob)
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
onBeforeUnmount(cleanup)
</script>

<template>
  <div class="backdrop" @click.self="emit('close')" @keydown.esc="emit('close')">
    <section class="modal" role="dialog" aria-modal="true">
      <header>
        <strong>{{ file.name }}</strong>
        <button @click="emit('close')">Закрити</button>
      </header>
      <div class="modal-body">
        <p v-if="loading" class="muted">Завантаження…</p>
        <p v-else-if="error" class="error">{{ error }}</p>
        <pre v-else-if="text" class="code">{{ text }}</pre>
        <img v-else-if="imageUrl" :src="imageUrl" :alt="file.name" />
        <p v-else class="muted">
          Перегляд вмісту для цього типу файлу не підтримується (лише .xml як текст і .png як зображення).
        </p>
      </div>
    </section>
  </div>
</template>
