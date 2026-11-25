<script setup>
defineProps({
  title: { type: String, required: true },
  actionTo: { type: String, default: '' },
  actionText: { type: String, default: '' },
})
</script>

<template>
  <div class="empty">
    <span>{{ title }}</span>
    <RouterLink v-if="actionTo" :to="actionTo">{{ actionText }}</RouterLink>
    <slot />
  </div>
</template>
