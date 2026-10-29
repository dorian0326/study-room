<script setup>
import { onMounted, ref } from 'vue'
import { fetchHealth } from '../api/health.js'
import { auth } from '../auth.js'

const health = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    health.value = await fetchHealth()
  } catch (e) {
    error.value = String(e)
  }
})
</script>

<template>
  <h2>欢迎，{{ auth.user?.name }}</h2>
  <p>角色：{{ auth.user?.roles.join('、') }}</p>
  <p v-if="health">后端状态：{{ health.status }}（{{ health.database }}，{{ health.timezone }}）</p>
  <p v-else-if="error">后端不可用：{{ error }}</p>
</template>
