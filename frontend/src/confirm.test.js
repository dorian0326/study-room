import { describe, expect, it } from 'vitest'

import { confirmDialog, confirmState, promptDialog, settleConfirm } from './confirm.js'

describe('confirmDialog', () => {
  it('resolves true only after the user confirms', async () => {
    const pending = confirmDialog({ title: '取消预约', message: '确定取消？', danger: true })
    expect(confirmState.open).toBe(true)
    expect(confirmState.title).toBe('取消预约')
    expect(confirmState.danger).toBe(true)
    settleConfirm(true)
    await expect(pending).resolves.toBe(true)
    expect(confirmState.open).toBe(false)
    expect(confirmState.resolve).toBeNull()
  })

  it('cancels the dialog that is already open', async () => {
    const first = confirmDialog({ title: '第一次' })
    const second = confirmDialog({ title: '第二次' })
    await expect(first).resolves.toBe(false)
    expect(confirmState.title).toBe('第二次')
    settleConfirm(false)
    await expect(second).resolves.toBe(false)
  })
})

describe('promptDialog', () => {
  it('returns the typed text, or null when cancelled', async () => {
    const pending = promptDialog({ title: '申诉原因', placeholder: '请填写' })
    expect(confirmState.input).toBe(true)
    expect(confirmState.placeholder).toBe('请填写')
    confirmState.value = '设备故障'
    settleConfirm(true)
    await expect(pending).resolves.toBe('设备故障')

    const cancelled = promptDialog()
    settleConfirm(false)
    await expect(cancelled).resolves.toBeNull()
  })
})
