<script setup>
import { computed } from 'vue'

/** 预约 / 座位 / 自习室状态徽标：统一文案和颜色。 */
const props = defineProps({ status: { type: String, default: '' } })

const MAP = {
  RESERVED: ['已预约', 'brand'],
  ACTIVE: ['使用中', 'ok'],
  TEMP_LEAVE: ['暂离', 'warn'],
  COMPLETED: ['已完成', 'neutral'],
  CANCELLED: ['已取消', 'neutral'],
  ADMIN_CANCELLED: ['管理员取消', 'danger'],
  EXPIRED: ['已过期', 'neutral'],
  NO_SHOW: ['爽约', 'danger'],
  AVAILABLE: ['空闲', 'ok'],
  IN_USE: ['使用中', 'warn'],
  OCCUPIED: ['已占用', 'warn'],
  MAINTENANCE: ['维护中', 'danger'],
  DISABLED: ['停用', 'neutral'],
  CLOSED: ['关闭', 'neutral'],
  OPEN: ['开放', 'ok'],
}

const info = computed(
  () => MAP[String(props.status || '').toUpperCase()] || [props.status || '—', 'neutral'],
)
</script>

<template>
  <span class="badge" :class="`tone-${info[1]}`"><i class="dot" />{{ info[0] }}</span>
</template>

<style scoped>
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
</style>
