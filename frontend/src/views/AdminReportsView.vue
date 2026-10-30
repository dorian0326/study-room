<script setup>
import { onMounted, ref } from 'vue'
import { getToken } from '../api/client.js'

const report = ref(null)
const error = ref('')
/** 按浏览器本地日历格式化日期，避免采用 UTC 日期边界。 */
function dateForInput(value) {
  // 报表筛选日期与用户界面显示的日历日保持一致。
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const today = dateForInput(new Date())
const start = ref(dateForInput(new Date(Date.now() - 29 * 86400000)))
const end = ref(today)

/** 加载所选日期范围内的利用率、预约高峰和违规趋势。 */
async function loadReport() {
  // 接口会同时返回日期范围、指标口径和统计数值。
  error.value = ''
  try {
    const params = new URLSearchParams({ start: start.value, end: end.value })
    const response = await fetch(`/api/admin/reports?${params}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail ?? `请求失败（HTTP ${response.status}）`)
    report.value = data
  } catch (cause) {
    error.value = cause.message
  }
}

/** 下载相同日期范围的授权 XLSX 统计报表。 */
async function downloadExcel() {
  // 后端在内存中生成工作簿，浏览器接收后保存为下载文件。
  error.value = ''
  try {
    const params = new URLSearchParams({ start: start.value, end: end.value })
    const response = await fetch(`/api/admin/reports/export.xlsx?${params}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail ?? `导出失败（HTTP ${response.status}）`)
    }
    const file = await response.blob()
    const url = URL.createObjectURL(file)
    const link = document.createElement('a')
    link.href = url
    link.download = `study-room-report-${start.value}-${end.value}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
  } catch (cause) {
    error.value = cause.message
  }
}

/** 将后端返回的利用率比例格式化为百分数。 */
function utilizationPercent() {
  // 该比例为已签到预约时长除以座位计划开放时长。
  return report.value ? `${(report.value.utilization.rate * 100).toFixed(1)}%` : '—'
}

onMounted(loadReport)
</script>

<template>
  <header class="page-header">
    <div>
      <h2>统计报表</h2>
    </div>
  </header>
  <form class="filters" @submit.prevent="loadReport">
    <label>开始日期 <input v-model="start" type="date" required /></label>
    <label>结束日期 <input v-model="end" type="date" required /></label>
    <button>查询</button>
    <button type="button" :disabled="!report" @click="downloadExcel">导出 Excel</button>
  </form>
  <p v-if="error" class="error">{{ error }}</p>
  <template v-if="report">
    <section class="metrics">
      <article>
        <strong>{{ utilizationPercent() }}</strong
        ><span>座位利用率</span>
      </article>
      <article>
        <strong>{{ report.utilization.booked_hours }}</strong
        ><span>已预约小时</span>
      </article>
      <article>
        <strong>{{ report.utilization.available_hours }}</strong
        ><span>计划开放座位小时</span>
      </article>
      <article>
        <strong>{{ report.reservation_count }}</strong
        ><span>预约记录</span>
      </article>
    </section>
    <p class="hint">{{ report.definition.utilization }}</p>
    <section class="panel">
      <h3>预约高峰</h3>
      <p v-if="!report.booking_peaks.length">该期间没有预约。</p>
      <table v-else>
        <thead>
          <tr>
            <th>日期</th>
            <th>开始小时</th>
            <th>预约数</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in report.booking_peaks.slice(0, 20)" :key="`${row.day}-${row.hour}`">
            <td>{{ row.day }}</td>
            <td>{{ String(row.hour).padStart(2, '0') }}:00</td>
            <td>{{ row.reservations }}</td>
          </tr>
        </tbody>
      </table>
    </section>
    <section class="panel">
      <h3>违规趋势</h3>
      <p v-if="!report.violation_trends.length">该期间没有违规记录。</p>
      <table v-else>
        <thead>
          <tr>
            <th>日期</th>
            <th>类型</th>
            <th>记录数</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in report.violation_trends" :key="`${row.day}-${row.type}`">
            <td>{{ row.day }}</td>
            <td>{{ row.type }}</td>
            <td>{{ row.count }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </template>
</template>
