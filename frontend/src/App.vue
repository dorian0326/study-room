<script setup>
import { useRouter } from 'vue-router'
import { auth, can, logout } from './auth.js'

const router = useRouter()

/** 注销当前账号并返回登录页。 */
async function onLogout() {
  // 后端先撤销令牌，finally 负责清除浏览器中的当前登录状态。
  await logout()
  router.push('/login')
}
</script>

<template>
  <header class="nav">
    <strong>智慧自习室管理系统</strong>
    <template v-if="auth.user">
      <RouterLink to="/">首页</RouterLink>
      <RouterLink to="/workflows">预约自习室</RouterLink>
      <RouterLink to="/check-in">扫码签到</RouterLink>
      <RouterLink to="/violations">违规与申诉</RouterLink>
      <RouterLink to="/notifications">站内通知</RouterLink>
      <RouterLink v-if="can('room:manage')" to="/admin/config">系统配置</RouterLink>
      <RouterLink v-if="can('room:manage')" to="/admin/seats">座位管理</RouterLink>
      <RouterLink v-if="can('user:manage')" to="/admin/users">用户管理</RouterLink>
      <RouterLink v-if="can('stats:read')" to="/admin/reports">统计报表</RouterLink>
      <RouterLink v-if="can('appeal:manage')" to="/admin/appeals">申诉审核</RouterLink>
      <RouterLink to="/change-password">修改密码</RouterLink>
      <span class="spacer" />
      <span>{{ auth.user.name }}（{{ auth.user.student_no }}）</span>
      <button @click="onLogout">退出登录</button>
    </template>
    <template v-else>
      <span class="spacer" />
      <RouterLink to="/login">登录</RouterLink>
      <RouterLink to="/register">注册</RouterLink>
    </template>
  </header>
  <main><RouterView /></main>
</template>

<style>
body {
  font-family: system-ui, sans-serif;
  margin: 0;
}
.nav {
  display: flex;
  gap: 1rem;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #ddd;
}
.spacer {
  flex: 1;
}
main {
  padding: 1rem;
  max-width: 1100px;
}
form.card {
  display: grid;
  gap: 0.75rem;
  max-width: 320px;
}
.error {
  color: #c00;
}
.ok {
  color: #080;
}
</style>
