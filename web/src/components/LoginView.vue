<script setup>
import { ref } from 'vue'
import { api } from '../lib/api.js'

const emit = defineEmits(['logged-in'])
const mode = ref('login')
const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    const name =
      mode.value === 'login'
        ? await api.login(username.value, password.value)
        : await api.register(username.value, password.value)
    emit('logged-in', name)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="login">
    <form class="card" @submit.prevent="submit">
      <h1>Хмарне сховище</h1>
      <p class="muted">{{ mode === 'login' ? 'Увійдіть до свого особистого простору' : 'Створіть обліковий запис' }}</p>
      <label>Логін <input v-model="username" autocomplete="username" required /></label>
      <label>
        Пароль
        <input
          v-model="password"
          type="password"
          :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
          required
        />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="primary" :disabled="busy">{{ mode === 'login' ? 'Увійти' : 'Зареєструватися' }}</button>
      <button type="button" class="link" @click="mode = mode === 'login' ? 'register' : 'login'; error = ''">
        {{ mode === 'login' ? 'Немає облікового запису? Зареєструватися' : 'Вже є обліковий запис? Увійти' }}
      </button>
    </form>
  </main>
</template>
