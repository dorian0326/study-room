<script setup>
import sillyUrl from '../assets/nailong/nailong-silly.webp'

defineProps({
  label: { type: String, default: '奶龙正在加载…' },
})
</script>

<template>
  <div class="nl-loading" role="status">
    <img :src="sillyUrl" alt="" />
    <span>{{ label }}</span>
  </div>
</template>
