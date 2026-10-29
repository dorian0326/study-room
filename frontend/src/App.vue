<script setup>
import { onMounted, ref } from 'vue'
import { fetchHealth } from './api/health.js'

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
  <main>
    <h1>智慧自习室管理系统</h1>
    <p v-if="health">
      后端状态：{{ health.status }}（{{ health.database }}，{{ health.timezone }}）
    </p>
    <p v-else-if="error">后端不可用：{{ error }}</p>
    <p v-else>正在连接后端…</p>
  </main>
</template>
