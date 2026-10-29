<script setup>
import { useRouter } from 'vue-router'
import { auth, can, logout } from './auth.js'

const router = useRouter()

/** 注销当前账号并返回登录页。 */
async function onLogout() {
  await logout()
  router.push('/login')
}
</script>

<template>
  <header class="nav">
    <div class="brand">
      <strong>智慧自习室</strong>
    </div>
    <nav v-if="auth.user" class="links">
      <RouterLink to="/">首页</RouterLink>
      <RouterLink to="/workflows">预约</RouterLink>
      <RouterLink to="/check-in">签到</RouterLink>
      <RouterLink to="/violations">违规</RouterLink>
      <RouterLink to="/notifications">通知</RouterLink>
      <RouterLink v-if="can('room:manage')" to="/admin/config">配置</RouterLink>
      <RouterLink v-if="can('room:manage')" to="/admin/seats">座位</RouterLink>
      <RouterLink v-if="can('user:manage')" to="/admin/users">用户</RouterLink>
      <RouterLink v-if="can('stats:read')" to="/admin/reports">报表</RouterLink>
      <RouterLink v-if="can('appeal:manage')" to="/admin/appeals">申诉</RouterLink>
      <RouterLink v-if="can('audit_log:read') || can('system_log:read')" to="/admin/logs">
        日志
      </RouterLink>
      <RouterLink v-if="can('system:backup') || can('system_log:read')" to="/admin/ops">
        备份监控
      </RouterLink>
      <RouterLink v-if="can('entry_exit:read')" to="/admin/gate">出入馆</RouterLink>
      <RouterLink to="/change-password">改密</RouterLink>
    </nav>
    <div class="account">
      <template v-if="auth.user">
        <span class="who">{{ auth.user.name }}（{{ auth.user.student_no }}）</span>
        <button type="button" @click="onLogout">退出</button>
      </template>
      <template v-else>
        <RouterLink to="/login">登录</RouterLink>
        <RouterLink to="/register">注册</RouterLink>
      </template>
    </div>
  </header>
  <main><RouterView /></main>
</template>

<style scoped>
.nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1rem;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--line);
  background: #fff;
  position: sticky;
  top: 0;
  z-index: 10;
}
.brand {
  white-space: nowrap;
}
.links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem 0.9rem;
  align-items: center;
  flex: 1;
  min-width: 12rem;
}
.account {
  display: flex;
  gap: 0.6rem;
  align-items: center;
  margin-left: auto;
}
.who {
  color: var(--muted);
  font-size: 0.92rem;
}
main {
  padding: 1rem;
  max-width: 1100px;
  margin: 0 auto;
}
</style>
