<script setup>
/** 轻量线性图标集（自绘 SVG 路径，24×24，描边风格）。 */
defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 26 },
  bold: { type: Boolean, default: false },
})

const PATHS = {
  home: 'M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z',
  calendar: 'M4 6h16v15H4zM4 10h16M8 3v4M16 3v4M8 14h3M8 17h6',
  qr: 'M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h2v2h-2zM18 14h2M14 18h2v2M18 18h2v2h-2z',
  alert: 'M12 3 2 20h20zM12 10v4M12 17v.5',
  bell: 'M6 16V11a6 6 0 1 1 12 0v5l2 2H4zM10 20a2 2 0 0 0 4 0',
  building: 'M4 21V5l8-3 8 3v16M9 21v-4h6v4M8 8h2M14 8h2M8 12h2M14 12h2M2 21h20',
  seat: 'M6 4h12v8H6zM4 12h16v3H4zM6 15v6M18 15v6',
  users:
    'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21a7 7 0 0 1 14 0M16 3.5a4 4 0 0 1 0 7.5M18 14a6 6 0 0 1 4 7',
  chart: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  gavel: 'M14 4l6 6M11 7l6 6M9 9l-6 6 3 3 6-6M12.5 5.5l6 6M3 21h10',
  logs: 'M5 3h10l4 4v14H5zM15 3v4h4M8 11h8M8 15h8M8 19h5',
  server: 'M4 4h16v6H4zM4 14h16v6H4zM8 7h.01M8 17h.01',
  door: 'M5 21V4l9-1v18M14 5h5v16M11 12v.5M2 21h20',
  more: 'M5 12h.01M12 12h.01M19 12h.01',
  sun: 'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4',
  moon: 'M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z',
  key: 'M15 7a4 4 0 1 1-3.5 6L4 20.5V17h3v-3h3l1.5-1.5',
  logout: 'M15 4h4v16h-4M10 8l-4 4 4 4M6 12h11',
  book: 'M4 19V5a2 2 0 0 1 2-2h13v15H6a2 2 0 0 0-2 2zm0 0a2 2 0 0 0 2 2h13M9 7h6',
  search: 'M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM21 21l-5-5',
}
</script>

<template>
  <svg
    class="x-icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="bold ? 2.4 : 1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path :d="PATHS[name] || PATHS.more" />
  </svg>
</template>
