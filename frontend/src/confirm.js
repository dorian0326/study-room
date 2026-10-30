import { reactive } from 'vue'

/** 全局确认对话框状态：替代浏览器原生 confirm()，样式与取消预约弹窗一致。 */
export const confirmState = reactive({
  open: false,
  title: '',
  message: '',
  confirmText: '确定',
  cancelText: '返回',
  danger: false,
  input: false,
  value: '',
  placeholder: '',
  resolve: null,
})

/**
 * 打开确认框并等待用户选择。
 * @param {{title?: string, message?: string, confirmText?: string, cancelText?: string, danger?: boolean}} options
 * @returns {Promise<boolean>} 点击确认为 true，返回/遮罩/Esc 为 false
 */
export function confirmDialog(options = {}) {
  if (confirmState.resolve) confirmState.resolve(false)
  return new Promise((resolve) => {
    Object.assign(confirmState, {
      open: true,
      title: options.title || '请确认',
      message: options.message || '',
      confirmText: options.confirmText || '确定',
      cancelText: options.cancelText || '返回',
      danger: Boolean(options.danger),
      input: false,
      value: '',
      placeholder: '',
      resolve,
    })
  })
}

/**
 * 打开带输入框的对话框，替代浏览器原生 prompt()。
 * @returns {Promise<string|null>} 确认时返回输入内容，取消返回 null
 */
export function promptDialog(options = {}) {
  if (confirmState.resolve) confirmState.resolve(false)
  return new Promise((resolve) => {
    Object.assign(confirmState, {
      open: true,
      title: options.title || '请输入',
      message: options.message || '',
      confirmText: options.confirmText || '提交',
      cancelText: options.cancelText || '返回',
      danger: Boolean(options.danger),
      input: true,
      value: '',
      placeholder: options.placeholder || '',
      resolve: (ok) => resolve(ok ? confirmState.value : null),
    })
  })
}

/** 关闭确认框并回传结果。 */
export function settleConfirm(result) {
  const resolve = confirmState.resolve
  confirmState.open = false
  confirmState.resolve = null
  if (resolve) resolve(result)
}
