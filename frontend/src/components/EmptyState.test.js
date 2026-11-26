import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import EmptyState from './EmptyState.vue'

const stubs = {
  RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
}

describe('EmptyState', () => {
  it('shows only the title when there is no action', () => {
    const wrapper = mount(EmptyState, {
      props: { title: '还没有预约' },
      global: { stubs },
    })
    expect(wrapper.text()).toBe('还没有预约')
    expect(wrapper.find('a').exists()).toBe(false)
  })

  it('links to the next step when an action is given', () => {
    const wrapper = mount(EmptyState, {
      props: { title: '还没有预约', actionTo: '/workflows', actionText: '去预约' },
      global: { stubs },
    })
    expect(wrapper.get('a').text()).toBe('去预约')
    expect(wrapper.get('a').attributes('href')).toBe('/workflows')
  })
})
