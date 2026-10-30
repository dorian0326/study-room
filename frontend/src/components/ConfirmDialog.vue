<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { confirmState, settleConfirm } from '../confirm.js'

const okButton = ref(null)
const field = ref(null)

function onKey(event) {
  if (!confirmState.open) return
  if (event.key === 'Escape') settleConfirm(false)
}

watch(
  () => confirmState.open,
  async (open) => {
    if (open) {
      await nextTick()
      const target = confirmState.input ? field.value : okButton.value
      target?.focus()
    }
  },
)
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Transition name="dlg">
    <div v-if="confirmState.open" class="dialog-mask" @click.self="settleConfirm(false)">
      <div
        class="dialog confirm-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
      >
        <h3 id="confirm-title">{{ confirmState.title }}</h3>
        <p v-if="confirmState.message" class="confirm-msg">{{ confirmState.message }}</p>
        <textarea
          v-if="confirmState.input"
          ref="field"
          v-model="confirmState.value"
          :placeholder="confirmState.placeholder"
          rows="3"
        ></textarea>
        <div class="dialog-actions">
          <button type="button" @click="settleConfirm(false)">{{ confirmState.cancelText }}</button>
          <button
            ref="okButton"
            type="button"
            :class="confirmState.danger ? 'danger solid' : 'brand'"
            @click="settleConfirm(true)"
          >
            {{ confirmState.confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.confirm-msg {
  color: var(--muted);
  white-space: pre-line;
}
</style>
