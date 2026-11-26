import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import StatusBadge from './StatusBadge.vue'

describe('StatusBadge', () => {
  it('shows the shared label for a known status', () => {
    const wrapper = mount(StatusBadge, { props: { status: 'temp_leave' } })
    expect(wrapper.text()).toBe('暂离')
    expect(wrapper.classes()).toContain('tone-warn')
  })

  it('keeps an unknown status readable', () => {
    const wrapper = mount(StatusBadge, { props: { status: '' } })
    expect(wrapper.text()).toBe('—')
    expect(wrapper.classes()).toContain('tone-neutral')
  })
})
