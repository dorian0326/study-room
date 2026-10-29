<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client.js'

const appeals = ref([])
const error = ref('')
const notice = ref('')

/** 加载等待管理员审核的申诉记录。 */
async function loadAppeals() {
  // 只有具备申诉管理权限的账号才能读取审核内容。
  error.value = ''
  try {
    appeals.value = await api('/admin/appeals?pending_only=true')
  } catch (cause) {
    error.value = cause.message
  }
}

/** 保存申诉通过或驳回结论，并记录对申请人可见的审核说明。 */
async function reviewAppeal(appeal, result) {
  const reviewComment = window.prompt(result === 'approved' ? '填写通过原因' : '填写驳回原因')
  if (!reviewComment || reviewComment.trim().length < 2) return
  error.value = ''
  notice.value = ''
  try {
    await api(`/admin/appeals/${appeal.id}`, {
      method: 'PATCH',
      body: { result, review_comment: reviewComment },
    })
    notice.value = `申诉 #${appeal.id} 已处理，用户会收到站内通知。`
    await loadAppeals()
  } catch (cause) {
    error.value = cause.message
  }
}

/** 将申诉截止时间转换为本地易读格式。 */
function formatDeadline(value) {
  // 显示七天申诉期限，方便管理员安排审核顺序。
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(loadAppeals)
</script>

<template>
  <h2>违规申诉审核</h2>
  <p v-if="error" class="error">{{ error }}</p>
  <p v-if="notice" class="ok">{{ notice }}</p>
  <p v-if="!appeals.length">当前没有待审核申诉。</p>
  <section v-for="appeal in appeals" :key="appeal.id" class="panel">
    <h3>申诉 #{{ appeal.id }} · 用户 {{ appeal.user_id }} · 违规 #{{ appeal.violation_id }}</h3>
    <p><strong>理由：</strong>{{ appeal.reason }}</p>
    <p v-if="appeal.evidence"><strong>证据说明：</strong>{{ appeal.evidence }}</p>
    <p>审核期限：{{ formatDeadline(appeal.deadline) }}</p>
    <div class="actions">
      <button @click="reviewAppeal(appeal, 'approved')">通过申诉</button>
      <button @click="reviewAppeal(appeal, 'rejected')">驳回申诉</button>
    </div>
  </section>
</template>

<style scoped>
.panel { margin: 1rem 0; padding: 1rem; border: 1px solid #d9e2dc; border-radius: 0.75rem; }
.actions { display: flex; gap: 0.5rem; }
</style>
