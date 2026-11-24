/** 座位区域、违规类型等前端展示文案。未知值原样返回。 */

export const ZONE_LABELS = {
  quiet: '静音区',
  discussion: '讨论区',
  open: '开放区',
  exam_prep: '考研区',
}

export function zoneLabel(value) {
  if (!value) return '—'
  return ZONE_LABELS[value] || value
}

export const VIOLATION_TYPE_LABELS = {
  left_undeclared: '离开未声明',
  temp_leave_timeout: '暂离超时未归',
  no_show: '预约未到（爽约）',
  no_checkout: '未签退',
  late_cancel: '迟到取消',
}

export function violationTypeLabel(value) {
  if (!value) return '—'
  const key = String(value).toLowerCase()
  return VIOLATION_TYPE_LABELS[key] || value
}

/** 座位设施摘要，例如「电源·靠窗」。 */
export function facilityText(seat) {
  if (!seat) return '—'
  const bits = []
  if (seat.has_power) bits.push('电源')
  if (seat.by_window) bits.push('靠窗')
  if (seat.accessible) bits.push('无障碍')
  return bits.length ? bits.join('·') : '—'
}
