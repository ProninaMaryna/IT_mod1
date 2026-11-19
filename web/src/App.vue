<script setup>
import { ref } from 'vue'
import { session, api } from './lib/api.js'
import LoginView from './components/LoginView.vue'
import FilesView from './components/FilesView.vue'

const user = ref(session.current?.username || null)

function onLogin(name) {
  user.value = name
}
function onLogout() {
  api.logout()
  user.value = null
}
</script>

<template>
  <LoginView v-if="!user" @logged-in="onLogin" />
  <FilesView v-else :username="user" @logout="onLogout" />
</template>
