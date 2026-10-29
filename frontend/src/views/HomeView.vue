<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client.js'
import { auth } from '../auth.js'

const health = ref(null)
const error = ref('')

/** 加载首页展示的 API 健康状态摘要。 */
async function loadHealth() {
  // 健康检查失败只展示在首页，不阻止用户继续使用其他业务页面。
  try {
    health.value = await api('/health')
  } catch (cause) {
    error.value = String(cause)
  }
}

onMounted(loadHealth)
</script>

<template>
  <h2>欢迎，{{ auth.user?.name }}</h2>
  <p>角色：{{ auth.user?.roles.join('、') }}</p>
  <p v-if="health">后端状态：{{ health.status }}（{{ health.database }}，{{ health.timezone }}）</p>
  <p v-else-if="error">后端不可用：{{ error }}</p>
  <p>在工作台管理预约、座位、违规申诉、站内通知和统计报表。</p>
  <RouterLink to="/workflows">打开业务工作台</RouterLink>
</template>
