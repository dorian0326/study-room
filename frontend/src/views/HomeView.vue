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
  <p>可浏览自习室与座位、创建/改约/取消预约，并用桌上二维码签到。</p>
  <p>
    <RouterLink to="/workflows">预约自习室</RouterLink>
    ·
    <RouterLink to="/check-in">扫码签到</RouterLink>
  </p>
</template>
